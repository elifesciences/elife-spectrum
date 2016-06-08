from os import path

from spectrum import aws

class InputBucket:
    def __init__(self, s3, bucket_name):
        self._s3 = s3
        self._bucket_name = bucket_name

    def upload(self, filename):
        self._s3.meta.client.upload_file(filename, self._bucket_name, path.basename(filename))
        print "Uploaded %s to %s" % (filename, self._bucket_name)

PRODUCTION_BUCKET = InputBucket(aws.S3, aws.SETTINGS.bucket_input)
