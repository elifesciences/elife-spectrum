import re
import datetime

import polling
import requests
from spectrum import aws

class TimeoutException(RuntimeError):
    pass

class BucketFileCheck:
    def __init__(self, s3, bucket_name, key):
        self._s3 = s3
        self._bucket_name = bucket_name
        self._key = key

    def of(self, **kwargs):
        criteria = self._key.format(**kwargs)
        try:
            polling.poll(
                lambda: self._is_present(criteria),
                timeout=120,
                step=5
            )
        except polling.TimeoutException:
            timestamp = datetime.datetime.today().isoformat()
            raise TimeoutException(
                "Cannot find object matching criteria %s in %s. Giving up at %s" \
                        % (criteria, self._bucket_name, timestamp)
            )

    def _is_present(self, criteria):
        bucket = self._s3.Bucket(self._bucket_name)
        bucket.load()
        for file in bucket.objects.all():
            if re.match(criteria, file.key):
                print "Found %s in bucket %s" % (file.key, self._bucket_name)
                return True
        return False

class WebsiteArticleCheck:
    def __init__(self, host, user, password):
        self._host = host
        self._user = user
        self._password = password

    def unpublished(self, id, version=1):
        try:
            article = polling.poll(
                # try to put some good error message here
                lambda: self._is_present(id, version),
                timeout=60,
                step=5
            )
        except polling.TimeoutException:
            timestamp = datetime.datetime.today().isoformat()
            raise TimeoutException(
                    "Cannot find article on website: /api/article/%s.%s.json; Giving up at %s" \
                        % (criteria, self._bucket_name, timestamp)
            )
        assert article['article-id'] == id, \
                "The article id does not correspond to the one we were looking for"
        assert article['publish'] is False, \
                "The article 'publish' status is not False: %s" % article

    def _is_present(self, id, version):
        template = "%s/api/article/%s.%s.json"
        url = template % (self._host, id, version)
        response = requests.get(url, auth=(self._user, self._password))
        if response.status_code == 200:
            print "Found %s on website" % url
            return response.json()
        return False

EIF = BucketFileCheck(aws.S3, aws.SETTINGS.bucket_eif, '{id}.1/.*/elife-{id}-v{version}.json')
WEBSITE = WebsiteArticleCheck(
    host=aws.SETTINGS.website_host,
    user=aws.SETTINGS.website_user,
    password=aws.SETTINGS.website_password
)
IMAGES = BucketFileCheck(aws.S3, aws.SETTINGS.bucket_cdn, '{id}/elife-{id}-{figure_name}-v{version}.jpg')
PDF = BucketFileCheck(aws.S3, aws.SETTINGS.bucket_cdn, '{id}/elife-{id}-v{version}.pdf')
