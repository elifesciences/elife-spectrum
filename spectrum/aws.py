import boto3
import settings as settingsLib

settings = settingsLib.get_settings('end2end')
s3 = boto3.resource('s3', aws_access_key_id = settings.aws_access_key_id, aws_secret_access_key = settings.aws_secret_access_key)

def clean():
    for bucket_name in [settings.bucket_input, settings.bucket_eif]:
        bucket = s3.Bucket(bucket_name)
        bucket.load()
        for file in bucket.objects.all():
            file.delete()
            print("Deleted %s:%s" % (bucket_name, file.key))
