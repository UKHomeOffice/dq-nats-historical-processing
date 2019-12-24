import boto3
from collections import defaultdict
import os
import botocore
import logging
from urllib.parse import unquote
from logging.handlers import TimedRotatingFileHandler
import csv
import random
import string


BATCH_SIZE               = int(os.environ['BATCH_SIZE'])
S3_SRC_ACCESS_KEY_ID     = os.environ['S3_SRC_ACCESS_KEY_ID']
S3_SRC_SECRET_ACCESS_KEY = os.environ['S3_SRC_SECRET_ACCESS_KEY']
S3_REGION_NAME           = os.environ['S3_REGION_NAME']
SLACK_WEBHOOK            = os.environ['SLACK_WEBHOOK']
S3_SRC_BUCKET_NAME       = os.environ['S3_SRC_BUCKET_NAME']
S3_SRC_KEY_PREFIX        = os.environ['S3_SRC_KEY_PREFIX']
BASE_PATH                = '/NATS/stage/'
LOG_SUFFIX               = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10)) + ".log"
LOG_FILE                 = '/NATS/log/nats_hist_batch_setup' + LOG_SUFFIX
CSV_SUFFIX               = S3_SRC_KEY_PREFIX.split('/')[-1]

def send_message_to_slack(text):
    """
    Formats the text and posts to a specific Slack web app's URL
    Returns:
        Slack API repsonse
    """
    logger = logging.getLogger()
    try:
        post = {
            "text": ":fire: :sad_parrot: An error has occured in the *NATS* pod :sad_parrot: :fire:",
            "attachments": [
                {
                    "text": "{0}".format(text),
                    "color": "#B22222",
                    "attachment_type": "default",
                    "fields": [
                        {
                            "title": "Priority",
                            "value": "High",
                            "short": "false"
                        }
                    ],
                    "footer": "Kubernetes API",
                    "footer_icon": "https://platform.slack-edge.com/img/default_application_icon.png"
                }
            ]
            }
        json_data = json.dumps(post)
        req = urllib.request.Request(url=SLACK_WEBHOOK,
                                     data=json_data.encode('utf-8'),
                                     headers={'Content-Type': 'application/json'})
        resp = urllib.request.urlopen(req)
        return resp

    except Exception as err:
        logger.error(
            'The following error has occurred on line: %s',
            sys.exc_info()[2].tb_lineno)
        logger.error(str(err))
        sys.exit(1)

def get_matching_s3_objects(bucket, prefix="", suffix=""):
    """
    Generate objects in an S3 bucket.

    :param bucket: Name of the S3 bucket.
    :param prefix: Only fetch objects whose key starts with
        this prefix (optional).
    :param suffix: Only fetch objects whose keys end with
        this suffix (optional).
    """
    boto_s3_session = boto3.Session(
        aws_access_key_id=S3_SRC_ACCESS_KEY_ID,
        aws_secret_access_key=S3_SRC_SECRET_ACCESS_KEY,
        region_name=S3_REGION_NAME
    )
    s3 = boto_s3_session.client('s3')
    paginator = s3.get_paginator("list_objects_v2")

    kwargs = {'Bucket': bucket}

    # We can pass the prefix directly to the S3 API.  If the user has passed
    # a tuple or list of prefixes, we go through them one by one.
    if isinstance(prefix, str):
        prefixes = (prefix, )
    else:
        prefixes = prefix

    for key_prefix in prefixes:
        kwargs["Prefix"] = key_prefix

        for page in paginator.paginate(**kwargs):
            try:
                contents = page["Contents"]
            except KeyError:
                return

            for obj in contents:
                key = obj["Key"]
                if key.endswith(suffix):
                    yield obj


def get_matching_s3_keys(bucket, prefix="", suffix=""):
    """
    Generate the keys in an S3 bucket.

    :param bucket: Name of the S3 bucket.
    :param prefix: Only fetch keys that start with this prefix (optional).
    :param suffix: Only fetch keys that end with this suffix (optional).
    """
    for obj in get_matching_s3_objects(bucket, prefix, suffix):
        yield obj["Key"]


def main():
    """
    Setup Logging
    """
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    LOGFORMAT = '%(asctime)s\t%(name)s\t%(levelname)s\t%(message)s'
    FORM = logging.Formatter(LOGFORMAT)
    logging.basicConfig(
        format=LOGFORMAT,
        level=logging.INFO
    )
    if logger.hasHandlers():
        logger.handlers.clear()
    LOGHANDLER = TimedRotatingFileHandler(LOG_FILE, when="midnight", interval=1, backupCount=7)
    LOGHANDLER.suffix = "%Y-%m-%d"
    LOGHANDLER.setFormatter(FORM)
    CONSOLEHANDLER = logging.StreamHandler()
    CONSOLEHANDLER.setFormatter(FORM)
    logger.addHandler(CONSOLEHANDLER)
    logger.info('Geting List of S3 Files for Download')
    new_dict = defaultdict(list)
    i=0
    for n,key in enumerate(get_matching_s3_keys(bucket=S3_SRC_BUCKET_NAME, prefix=S3_SRC_KEY_PREFIX, suffix='.json')):
        if(n % BATCH_SIZE == 0):
            i=i+1
        new_dict['batch' + str(i)].append(key)

    logger.info('Batch Schedule Prepared')


    with open(f'{BASE_PATH}/batchfile{CSV_SUFFIX}.csv', 'w', newline="") as csv_file:
        writer = csv.writer(csv_file)
        for key, value in new_dict.items():
            writer.writerow([key, value])

    logger.info('Batch CSV Written Successfully')

if __name__ == '__main__':
    main()
