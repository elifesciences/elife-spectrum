import backoff
import requests
from spectrum import logger

LOGGER = logger.logger(__name__)


def retry_request(response):
    return response.status_code in [502, 504]


def _retrying_request(details):
    LOGGER.debug("%s, will retry: %s", details['value'].status_code, details['args'][0])


# intended behavior at the moment: if the page is too slow to load,
# timeouts will cut it (a CDN may serve a stale version if it has it)
@backoff.on_predicate(backoff.expo, predicate=retry_request, max_tries=3, on_backoff=_retrying_request)
def persistently_get(url, **kwargs):
    return requests.get(url, **kwargs)
