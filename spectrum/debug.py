import socket
from spectrum import logger

LOGGER = logger.logger(__name__)

def get_host_ip(host):
    try:
        return socket.gethostbyname(host)
    except socket.gaierror:
        LOGGER.exception("Cannot lookup host: %s", host)
        return None
