
class MailcatcherCheck():
    def __init__(self, url):
        self._url = url

    def wait_email(self, subject):
        pass

#
#  curl -v end2end--bot.elifesciences.org:1080/messages | jq .
#  {
#    "id": 3,
#    "sender": "<features_team@example.org> size=51291",
#    "recipients": [
#      "<features_team@example.org>"
#    ],
#    "subject": "Digest: Anonymous_7563686500967715893",
#    "size": "51975",
#    "created_at": "2018-07-31T13:52:22+00:00"
#  },
#  {
#    "id": 4,
#    "sender": "<features_team@example.org> size=51284",
#    "recipients": [
#      "<exeter@example.org>"
#    ],
#    "subject": "Digest: Anonymous_7563686500967715893",
#    "size": "51968",
#    "created_at": "2018-07-31T13:52:22+00:00"
#  }
#]
#

