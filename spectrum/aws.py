import datetime
import logging
import re

import boto3
import settings

LOGGER = logging.getLogger(__name__)
SETTINGS = settings.get_settings('end2end')
S3 = boto3.resource(
    's3',
    aws_access_key_id=SETTINGS.aws_access_key_id,
    aws_secret_access_key=SETTINGS.aws_secret_access_key
)
SWF = boto3.client(
    'swf',
    aws_access_key_id=SETTINGS.aws_access_key_id,
    aws_secret_access_key=SETTINGS.aws_secret_access_key
)
SQS = boto3.client(
    'sqs',
    aws_access_key_id=SETTINGS.aws_access_key_id,
    aws_secret_access_key=SETTINGS.aws_secret_access_key
)

def clean():
    open_workflow_executions = SWF.list_open_workflow_executions(
        domain='Publish.end2end',
        startTimeFilter={
            'oldestDate': datetime.datetime.now() - datetime.timedelta(days=1),
            'latestDate': datetime.datetime.now()
        }
    )
    assert 'executionInfos' in open_workflow_executions
    for workflow in open_workflow_executions['executionInfos']:
        SWF.terminate_workflow_execution(
            domain='Publish.end2end',
            workflowId=workflow['execution']['workflowId'],
            runId=workflow['execution']['runId'],
            reason='end2end testing environment cleanup'
        )
        LOGGER.info(
            "Terminated workflow: workflowId=%s runId=%s",
            workflow['execution']['workflowId'],
            workflow['execution']['runId']
        )

    all_buckets = S3.meta.client.list_buckets()['Buckets']
    buckets_to_clean = [b['Name'] for b in all_buckets if re.match(r".*end2end.*", b['Name'])]
    LOGGER.info("Cleaning up %d buckets: %s", len(buckets_to_clean), buckets_to_clean)
    for bucket_name in buckets_to_clean:
        bucket = S3.Bucket(bucket_name)
        bucket.load()
        for file in bucket.objects.all():
            file.delete()
            LOGGER.info(
                "Deleted %s:%s",
                bucket_name,
                file.key
            )

