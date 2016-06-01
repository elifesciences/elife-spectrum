import boto3
import settings as settingsLib
from datetime import datetime, timedelta

settings = settingsLib.get_settings('end2end')
s3 = boto3.resource('s3', aws_access_key_id = settings.aws_access_key_id, aws_secret_access_key = settings.aws_secret_access_key)
swf = boto3.client('swf', aws_access_key_id = settings.aws_access_key_id, aws_secret_access_key = settings.aws_secret_access_key)

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

    for bucket_name in [settings.bucket_input, settings.bucket_eif]:
        bucket = s3.Bucket(bucket_name)
        bucket.load()
        for file in bucket.objects.all():
            file.delete()
            print("Deleted %s:%s" % (bucket_name, file.key))

