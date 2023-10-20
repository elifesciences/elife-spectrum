from datetime import datetime
from pprint import pformat
import requests
from spectrum import logger

LOGGER = logger.logger(__name__)

class TimeoutError(RuntimeError):
    @staticmethod
    def giving_up_on(what, after=None):
        timestamp = datetime.today().isoformat()
        msg = "Cannot find '%s'; Giving up at %s" % (what, timestamp)
        if after:
            msg = "Cannot find '%s'; Giving up at %s after %s seconds" % (what, timestamp, after)
        return TimeoutError(msg)

class UnrecoverableError(RuntimeError):
    def __init__(self, details):
        super().__init__(details)
        self._details = details

    def __str__(self):
        if isinstance(self._details, requests.Response):
            return "RESPONSE CODE: %d\nRESPONSE BODY:\n%s\n" \
                    % (self._details.status_code, self._details.text)
        return "DETAILS: %s" % pformat(self._details)

def assert_status_code(response, expected_status_code, url):
    try:
        if response.status_code == 503:
            # https://docs.fastly.com/en/guides/common-503-errors
            LOGGER.error("503 response body: %s", response.text)
        assert response.status_code == expected_status_code, \
                "Response from %s had status %d\nHeaders: %s\nAssertion, not request, performed at %s" % (url, response.status_code, pformat(response.headers), datetime.now().isoformat())
            #"Response from %s had status %d, body %s" % (url, response.status_code, response.text)
    except UnicodeDecodeError as exc:
        LOGGER.exception("Unicode error on %s (status code %s)", url, response.status_code)
        LOGGER.error("(%s): type of content %s", url, type(response.content))
        LOGGER.error("(%s): apparent_encoding %s", url, response.apparent_encoding)
        with open("/tmp/response.content.txt", "w") as dump:
            dump.write(response.content)
        LOGGER.error("(%s): written response.text to /tmp")
        LOGGER.error("(%s): headers %s)", url, response.headers)
        error_msg = 'Could not decode response from %s (status code %s, headers %s)' % (url, response.status_code, response.headers)
        raise RuntimeError(error_msg) from exc
