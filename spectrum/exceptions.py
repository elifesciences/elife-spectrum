from datetime import datetime
from pprint import pformat
import requests
from spectrum import logger

LOGGER = logger.logger(__name__)

class TimeoutError(RuntimeError):
    @staticmethod
    def giving_up_on(what):
        timestamp = datetime.today().isoformat()
        return TimeoutError(
            "Cannot find '%s'; Giving up at %s" \
                    % (what, timestamp)
        )

class UnrecoverableError(RuntimeError):
    def __init__(self, details):
        super(UnrecoverableError, self).__init__(self, details)
        self._details = details

    def __str__(self):
        if isinstance(self._details, requests.Response):
            return "RESPONSE CODE: %d\nRESPONSE BODY:\n%s\n" \
                    % (self._details.status_code, self._details.text)
        else:
            return "DETAILS: %s" % pformat(self._details)

def assert_status_code(response, expected_status_code, url):
    try:
        assert response.status_code == expected_status_code, \
                "Response from %s had status %d\nHeaders: %s\nAssertion, not request, performed at %s" % (url, response.status_code, pformat(response.headers), datetime.now().isoformat())
            #"Response from %s had status %d, body %s" % (url, response.status_code, response.content)
    except UnicodeDecodeError:
        LOGGER.exception("Unicode error on %s (status code %s)", url, response.status_code)
        LOGGER.error("(%s): type of content %s", url, type(response.content))
        LOGGER.error("(%s): apparent_encoding %s", url, response.apparent_encoding)
        with open("/tmp/response_content.txt", "w") as dump:
            dump.write(response.content)
        LOGGER.error("(%s): written response.content to /tmp")
        LOGGER.error("(%s): headers %s)", url, response.headers)
        raise RuntimeError("Could not decode response from %s (status code %s, headers %s)" % (url, response.status_code, response.headers))
