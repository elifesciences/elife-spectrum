from aws import s3
import re
import time
import polling

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
                print("Found %s in bucket %s", (file.key, self._bucket_name))
                return True
        return False
        

eif = BucketFileCheck(s3, 'end2end-' + 'elife-publishing-eif', '{id}.1/.*/elife-{id}-v1.json')
