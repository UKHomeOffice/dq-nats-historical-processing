import boto3
from collections import defaultdict
import os
import botocore
import json
import logging
from urllib.parse import unquote
from logging.handlers import TimedRotatingFileHandler
import time
import concurrent.futures
import csv
from datetime import datetime

startTime = datetime.now()
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logging.getLogger('boto3').setLevel(logging.CRITICAL)
logging.getLogger('botocore').setLevel(logging.CRITICAL)
logging.getLogger('s3transfer').setLevel(logging.CRITICAL)
logging.getLogger('urllib3').setLevel(logging.CRITICAL)

#PROFILE="notprod"
#BUCKET_INPUT='s3-dq-nats-archive-notprod'
#PREFIX_INPUT='2018/new_test'
BASE_PATH = '/Users/sbommireddy/Documents/tmp/'
LOG_FILE = f'{BASE_PATH}/nats_hist_batch_download.log'

S3_ACCESS_KEY_ID        = os.environ['S3_ACCESS_KEY_ID']
S3_SECRET_ACCESS_KEY    = os.environ['S3_SECRET_ACCESS_KEY']
S3_REGION_NAME          = os.environ['S3_REGION_NAME']
SLACK_WEBHOOK           = os.environ['SLACK_WEBHOOK']
BUCKET_INPUT            = os.environ['BUCKET_INPUT']
PREFIX_INPUT            = os.environ['PREFIX_INPUT']
#BASE_PATH               = '/NATS/scripts'
#LOG_FILE                = '/NATS/log/nats_hist_batch_setup.log'

CSV_SUFFIX = PREFIX_INPUT.split('/')[-1]

'''
BUCKET_INPUT='s3-dq-nats-archive-prod'
PREFIX_INPUT='nats/2019/12/16'
'''
TPExecutor = concurrent.futures.ThreadPoolExecutor

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


def download(myfile):
        #session = boto3.Session(profile_name=PROFILE)
        boto_s3_session = boto3.Session(
            aws_access_key_id=S3_ACCESS_KEY_ID,
            aws_secret_access_key=S3_SECRET_ACCESS_KEY,
            region_name=S3_REGION_NAME
        )
        s3 = boto_s3_session.resource('s3')
        try:
            file_name = unquote(myfile.split('/')[-1])
            download_path = '{0}{1}'.format(BASE_PATH,file_name)
            s3.Bucket(BUCKET_INPUT).download_file(myfile, download_path)
            logger.info('File Downloaded')
        except botocore.exceptions.ClientError as err:
            if err.response['Error']['Code'] == "404":
                print("The object does not exist." , err)
            else:
                #raise
                error = str(err)
                print(error)
                send_message_to_slack(error)
        return myfile

def get_batch_data(csv_fname):
    with open(csv_fname, "r") as batch_files:
        for batch_file in csv.reader(batch_files):
            yield batch_file

def main():
    """
    Setup Logging
    """
    LOGFORMAT = '%(asctime)s\t%(name)s\t%(levelname)s\t%(threadName)s\t%(message)s'
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
    logger.info('Starting Download of S3 Files')

    filename = f'{BASE_PATH}/batchfile{CSV_SUFFIX}.csv'
    batch = iter(get_batch_data(filename))
    try:
        for row in batch:
            with TPExecutor(max_workers = 8) as thread_pool_executor:
                data_futures = [thread_pool_executor.submit(download, fname) for fname in eval(row[1])]
    except Exception as err:
        logger.error("Failure getting files from SFTP")
        logger.exception(str(err))
        error = str(err)
        send_message_to_slack(error)

    print("-----Processing Time of Download-------")
    print(datetime.now() - startTime)

if __name__ == '__main__':
    main()
