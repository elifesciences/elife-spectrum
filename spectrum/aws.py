import datetime
import re

import boto3
from spectrum.config import SETTINGS
from spectrum import logger

LOGGER = logger.logger(__name__)
S3 = boto3.resource(
    's3',
    aws_access_key_id=SETTINGS['aws_access_key_id'],
    aws_secret_access_key=SETTINGS['aws_secret_access_key'],
    region_name=SETTINGS['region_name']
)
SWF = boto3.client(
    'swf',
    aws_access_key_id=SETTINGS['aws_access_key_id'],
    aws_secret_access_key=SETTINGS['aws_secret_access_key'],
    region_name=SETTINGS['region_name']
)
SQS = boto3.client(
    'sqs',
    aws_access_key_id=SETTINGS['aws_access_key_id'],
    aws_secret_access_key=SETTINGS['aws_secret_access_key'],
    region_name=SETTINGS['region_name']
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
        clean_bucket(bucket_name)

def clean_bucket(bucket_name, prefix=None):
    msg = "Cleaning bucket %s" % bucket_name
    if prefix:
        msg = msg + " by prefix %s" % prefix
    LOGGER.debug(msg, extra={'id': id})
    bucket = S3.Bucket(bucket_name)
    bucket.load()
    all_objects = bucket.objects.all()
    if prefix:
        all_objects = all_objects.filter(Prefix=prefix)
    keys = [file.key for file in all_objects]
    batch_size = 100
    batches = [keys[lower:lower+batch_size] for lower in range(0, len(keys), batch_size)]
    for batch in batches:
        bucket.delete_objects(Delete={
            'Objects': [{'Key': key} for key in batch]
        })
        LOGGER.info(
            "Deleted from bucket %s the keys %s",
            bucket_name,
            batch
        )
