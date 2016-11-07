import logging
from os import path
import requests
from spectrum import aws

LOGGER = logging.getLogger(__name__)

class InputBucket:
    def __init__(self, s3, bucket_name):
        self._s3 = s3
        self._bucket_name = bucket_name

    def upload(self, filename, id):
        self._s3.meta.client.upload_file(filename, self._bucket_name, path.basename(filename))
        LOGGER.info("Uploaded %s to %s", filename, self._bucket_name, extra={'id': id})

    def name(self):
        return self._bucket_name

class Dashboard:
    def __init__(self, host, user, password):
        self._host = host
        self._user = user
        self._password = password

    def publish(self, id, version, run):
        template = "%s/api/queue_article_publication"
        url = template % self._host
        body = {}
        body = {'articles': [{'id': id, 'version': version, 'run': run}]}
        response = requests.post(url, auth=(self._user, self._password), json=body, verify=False)
        assert response.status_code == 200
        LOGGER.info(
            "Pressed Publish for %s version %s on dashboard",
            url,
            version,
            extra={'id': id}
        )


PRODUCTION_BUCKET = InputBucket(aws.S3, aws.SETTINGS.bucket_input)
DASHBOARD = Dashboard(
    aws.SETTINGS.dashboard_host,
    aws.SETTINGS.dashboard_user,
    aws.SETTINGS.dashboard_password
)
