FROM docker.io/debian

RUN apt update; \
	apt install -y zeroc-ice-compilers \
		zeroc-ice-slice \
		python3-zeroc-ice

COPY Murmur.ice cleaner.py /app/
WORKDIR /app
RUN /usr/bin/slice2py -I/usr/share/ice/slice Murmur.ice
USER daemon

ENTRYPOINT /usr/bin/python3 /app/cleaner.py
