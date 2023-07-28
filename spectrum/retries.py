"""utility library for polling URLs.

contains no tests that are run."""

import backoff
import requests
from spectrum import logger

LOGGER = logger.logger(__name__)

MAX_RETRIES = 3

def retry_request(response):
    retry_these = [
        # lsh@2021-07-27: added 404 as there appears to be a case in the interaction of iiif and journal-cms
        # where journal-cms doesn't have the image ready.
        404,
        # lsh@2021-09-21: added 400 as Observer will return a 400 bad request when a report is requested with
        # an unknown subject.
        400,
        502,
        504
    ]
    return response.status_code in retry_these


def _retrying_request(details):
    LOGGER.debug("%s, will retry: %s", details['value'].status_code, details['args'][0])


# intended behavior at the moment: if the page is too slow to load,
# timeouts will cut it (a CDN may serve a stale version if it has it)
@backoff.on_predicate(backoff.expo, predicate=retry_request, max_tries=MAX_RETRIES, on_backoff=_retrying_request)
def persistently_get(url, **kwargs):
    return requests.get(url, **kwargs)
