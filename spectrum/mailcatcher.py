import requests

from spectrum import logger, polling

LOGGER = logger.logger(__name__)

class MailcatcherCheck():
    def __init__(self, url):
        self._url = url

    def wait_email(self, subject):
        def _check():
            messages_url = "%s/messages" % self._url
            messages = requests.get(messages_url).json()
            matching = [m for m in messages if m['subject'] == subject]
            return (matching, messages)

        # [{
        #   "id": 3,
        #   "sender": "<features_team@example.org> size=51291",
        #   "recipients": [
        #     "<features_team@example.org>"
        #   ],
        #   "subject": "Digest: Anonymous_7563686500967715893",
        #   "size": "51975",
        #   "created_at": "2018-07-31T13:52:22+00:00"
        # }]
        (_, matching) = polling.poll(_check, "Cannot find email with subject %s", subject)
        LOGGER.info("Found matching messages: %s", matching)
