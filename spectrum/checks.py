import re
import datetime
import logging

import polling
import requests
from spectrum import aws

# TODO: install proper SSL certificate on elife-dashboard-develop--end2end to avoid this
requests.packages.urllib3.disable_warnings()

GLOBAL_TIMEOUT = 300
LOGGER = logging.getLogger(__name__)

class TimeoutException(RuntimeError):
    @staticmethod
    def giving_up_on(what):
        timestamp = datetime.datetime.today().isoformat()
        return TimeoutException(
            "Cannot find '%s'; Giving up at %s" \
                    % (what, timestamp)
        )

class BucketFileCheck:
    def __init__(self, s3, bucket_name, key):
        self._s3 = s3
        self._bucket_name = bucket_name
        self._key = key

    def of(self, **kwargs):
        criteria = self._key.format(**kwargs)
        try:
            return polling.poll(
                lambda: self._is_present(criteria, kwargs['id']),
                timeout=GLOBAL_TIMEOUT,
                step=5
            )
        except polling.TimeoutException:
            raise TimeoutException.giving_up_on(
                "object matching criteria %s in %s" \
                    % (criteria, self._bucket_name)
            )

    def _is_present(self, criteria, id):
        bucket = self._s3.Bucket(self._bucket_name)
        bucket.load()
        for file in bucket.objects.all():
            match = re.match(criteria, file.key)
            if match:
                LOGGER.info("Found %s in bucket %s", file.key, self._bucket_name, extra={'id': id})
                if match.groups():
                    LOGGER.info("Found groups %s in matching the file name" % match.groupdict())
                return match.groups()
        return False

class WebsiteArticleCheck:
    def __init__(self, host, user, password):
        self._host = host
        self._user = user
        self._password = password

    def unpublished(self, id, version=1):
        try:
            article = polling.poll(
                lambda: self._is_present(id, version),
                timeout=GLOBAL_TIMEOUT,
                step=5
            )
            assert article['article-id'] == id, \
                    "The article id does not correspond to the one we were looking for"
            assert article['publish'] is False, \
                    "The article 'publish' status is not False: %s" % article
            return article
        except polling.TimeoutException:
            raise TimeoutException.giving_up_on(
                "article on website: /api/article/%s.%s.json" \
                    % (id, version)
            )

    def _is_present(self, id, version):
        template = "%s/api/article/%s.%s.json"
        url = template % (self._host, id, version)
        response = requests.get(url, auth=(self._user, self._password))
        if response.status_code == 200:
            LOGGER.info("Found %s on website", url, extra={'id': id})
            return response.json()
        return False

class DashboardArticleCheck:
    def __init__(self, host, user, password):
        self._host = host
        self._user = user
        self._password = password

    def ready_to_publish(self, id, version):
        return self._wait_for_status(id, version, "ready to publish")

    def published(self, id, version):
        return self._wait_for_status(id, version, "published")

    def _wait_for_status(self, id, version, status):
        try:
            article = polling.poll(
                lambda: self._is_present(id, version, status),
                timeout=GLOBAL_TIMEOUT,
                step=5
            )
            return article
        except polling.TimeoutException:
            # TODO: duplication with _is_present
            raise TimeoutException.giving_up_on(
                "article version %s in status %s on dashboard: /api/article/%s" \
                    % (version, status, id)
            )

    def _is_present(self, id, version, status):
        template = "%s/api/article/%s"
        url = template % (self._host, id)
        version_key = str(version)
        response = requests.get(url, auth=(self._user, self._password), verify=False)
        if response.status_code != 200:
            return False
        if response.status_code >= 500:
            raise RuntimeError(response)
        article = response.json()
        if 'versions' not in article:
            return False
        if version_key not in article['versions']:
            return False
        version_details = article['versions'][version_key]['details']
        if version_details['publication-status'] != status:
            return False
        LOGGER.info("Found %s version %s in status %s on dashboard", url, version_key, status, extra={'id': id})
        return article

EIF = BucketFileCheck(
    aws.S3,
    aws.SETTINGS.bucket_eif,
    '{id}.{version}/(?P<run>.*)/elife-{id}-v{version}.json'
)
WEBSITE = WebsiteArticleCheck(
    host=aws.SETTINGS.website_host,
    user=aws.SETTINGS.website_user,
    password=aws.SETTINGS.website_password
)
IMAGES = BucketFileCheck(
    aws.S3,
    aws.SETTINGS.bucket_cdn,
    '{id}/elife-{id}-{figure_name}-v{version}.jpg'
)
PDF = BucketFileCheck(
    aws.S3,
    aws.SETTINGS.bucket_cdn,
    '{id}/elife-{id}-v{version}.pdf'
)
DASHBOARD = DashboardArticleCheck(
    host=aws.SETTINGS.dashboard_host,
    user=aws.SETTINGS.dashboard_user,
    password=aws.SETTINGS.dashboard_password
)
