import datetime
import logging
import sys

import Ice

import Murmur

INACTIVE_DAYS = 365
BAD_NAMES_DAYS = 1
BAD_NANES = [
    "Mumla_User",
    "Plumble_User",
]


def remove_bad_user_names(server):
    logger = logging.getLogger("mumble_cleaner")
    for user_id in server.getRegisteredUsers(""):
        user_info = server.getRegistration(user_id)
        user_name = user_info.get(Murmur.UserInfo.UserName)
        if user_name not in BAD_NANES:
            continue  # Skip good names
        last_activity = user_info.get(Murmur.UserInfo.UserLastActive)
        if last_activity:
            last_activity = datetime.datetime.strptime(
                last_activity, "%Y-%m-%d %H:%M:%S"
            )
            if last_activity > datetime.datetime.now() - datetime.timedelta(
                days=BAD_NAMES_DAYS
            ):
                continue  # Skip recently used accounts.
        logger.info(
            "Removing user #%i %s with bad name and last activity at %s",
            user_id,
            user_name,
            last_activity or "n/a",
        )
        server.unregisterUser(user_id)


def remove_inactive_users(server):
    logger = logging.getLogger("mumble_cleaner")
    for user_id in server.getRegisteredUsers(""):
        user_info = server.getRegistration(user_id)
        user_name = user_info.get(Murmur.UserInfo.UserName)
        if user_name == "SuperUser":
            continue  # Skip super user
        last_activity = user_info.get(Murmur.UserInfo.UserLastActive)
        if last_activity:
            last_activity = datetime.datetime.strptime(
                last_activity, "%Y-%m-%d %H:%M:%S"
            )
            if last_activity > datetime.datetime.now() - datetime.timedelta(
                days=INACTIVE_DAYS
            ):
                continue  # Skip recently used accounts.
        logger.info(
            "Removing user #%i %s with last activity at %s",
            user_id,
            user_name,
            last_activity or "n/a",
        )
        server.unregisterUser(user_id)


def remove_orphaned_channels(server):
    logger = logging.getLogger("mumble_cleaner")

    all_done = False
    while not all_done:
        all_done = True

        channels_with_children = {
            channel.parent for channel in server.getChannels().values()
        }

        for channel_id, channel in server.getChannels().items():
            if channel_id == 0:
                continue  # skip root channel
            if channel.temporary:
                continue  # skip temporary channels
            if channel_id in channels_with_children:
                continue  # skip channels with childrens
            acl, groups, inherit = server.getACL(channel_id)
            added = set()
            for group in groups:
                # Count only administrators
                if group.name == "admin":
                    added.update(set(group.add))
                    break
            if added:
                continue  # Channel has added users in groups
            logger.info(
                "Channel #%i %s has no users in groups", channel_id, channel.name
            )
            logger.info("Removing channel #%i %s", channel_id, channel.name)
            server.removeChannel(channel_id)
            all_done = False  # Repeat again


def reset_channel_position(server):
    logger = logging.getLogger("mumble_cleaner")
    parents = set()
    for channel_id, channel in server.getChannels().items():
        acl, groups, inherit = server.getACL(channel_id)
        for group in groups:
            if group.name != "no_position_for_children":
                continue
            logger.info(
                "Channel #%i %s restricts positions for children",
                channel_id,
                channel.name,
            )
            parents.add(channel_id)
            break
    for channel_id, channel in server.getChannels().items():
        if channel.parent not in parents:
            continue
        if channel.position == 0:
            continue
        logger.info(
            "Resetting position for channel #%i %s",
            channel_id,
            channel.name,
        )
        channel.position = 0
        server.setChannelState(channel)


def main():
    logger = logging.getLogger("mumble_cleaner")
    with Ice.initialize(sys.argv) as communicator:
        base = communicator.stringToProxy("Meta:tcp -h 127.0.0.1 -p 6502")

        meta = Murmur.MetaPrx.checkedCast(base)
        if not meta:
            raise RuntimeError("Invalid proxy")

        servers = meta.getAllServers()

        if len(servers) == 0:
            logger.info("No servers found")

        for current_server in servers:
            if current_server.isRunning():
                logger.info(
                    "Found server (id=%d):\tUptime %s",
                    current_server.id(),
                    datetime.timedelta(seconds=current_server.getUptime()),
                )
                remove_bad_user_names(current_server)
                remove_inactive_users(current_server)
                remove_orphaned_channels(current_server)
                reset_channel_position(current_server)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    main()
