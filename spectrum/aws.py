import boto3
import settings as settingsLib
import re
from datetime import datetime, timedelta

settings = settingsLib.get_settings('end2end')
s3 = boto3.resource('s3', aws_access_key_id = settings.aws_access_key_id, aws_secret_access_key = settings.aws_secret_access_key)
swf = boto3.client('swf', aws_access_key_id = settings.aws_access_key_id, aws_secret_access_key = settings.aws_secret_access_key)
sqs = boto3.client('sqs', aws_access_key_id = settings.aws_access_key_id, aws_secret_access_key = settings.aws_secret_access_key)

def clean():
    for workflow in swf.list_open_workflow_executions(
        domain = 'Publish.end2end',
        startTimeFilter={
            'oldestDate': datetime.now() - timedelta(days=1),
            'latestDate': datetime.now()
        }
    )['executionInfos']:
        swf.terminate_workflow_execution(
            domain = 'Publish.end2end',
            workflowId = workflow['execution']['workflowId'],
            runId = workflow['execution']['runId'],
            reason = 'end2end testing environment cleanup'
        )
        print("Terminated workflow: workflowId=%s runId=%s" % (workflow['execution']['workflowId'], workflow['execution']['runId']))

    buckets_to_clean = [b['Name'] for b in s3.meta.client.list_buckets()['Buckets'] if re.match(r".*end2end.*", b['Name'])]
    print("Cleaning up %d buckets: %s" % (len(buckets_to_clean), buckets_to_clean))
    for bucket_name in buckets_to_clean:
        bucket = s3.Bucket(bucket_name)
        bucket.load()
        for file in bucket.objects.all():
            file.delete()
            print("Deleted %s:%s" % (bucket_name, file.key))

