from datetime import datetime
from pprint import pformat
import requests

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

