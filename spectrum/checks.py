from aws import s3, settings
import re
import time
import polling
import requests

class BucketFileCheck:
    def __init__(self, s3, bucket_name, key):
        self._s3 = s3
        self._bucket_name = bucket_name
        self._key = key

    def of(self, **kwargs):
        criteria = self._key.format(**kwargs)
        polling.poll(
            lambda: self._is_present(criteria),
            timeout=60,
            step=5
        )

    def _is_present(self, criteria):
        bucket = self._s3.Bucket(self._bucket_name)
        bucket.load()
        for file in bucket.objects.all():
            if re.match(criteria, file.key):
                print("Found %s in bucket %s" % (file.key, self._bucket_name))
                return True
        return False

class WebsiteArticleCheck:
    def __init__(self, host, user, password):
        self._host = host
        self._user = user
        self._password = password

    def unpublished(self, id):
        article = polling.poll(
            # try to put some good error message here
            lambda: self._is_present(id),
            timeout=60,
            step=5
        )
        assert article['article-id'] == id, "The article id does not correspond to the one we were looking for"
        assert article['publish'] == False, "The article 'publish' status is not False: %s" % article

    def _is_present(self, id):
        template = "%s/api/article/%s.1.json"
        url = template % (self._host, id)
        r = requests.get(url, auth=(self._user, self._password))
        if r.status_code == 200:
            print("Found %s on website" % url)
            return r.json()
        return False

eif = BucketFileCheck(s3, settings.bucket_eif, '{id}.1/.*/elife-{id}-v1.json')
website = WebsiteArticleCheck(host=settings.website_host, user=settings.website_user, password=settings.website_password)
images = BucketFileCheck(s3, 'end2end-elife-publishing-cdn', '{id}/elife-{id}-{figure_name}-v1.jpg')
