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
import random
import string

startTime = datetime.now()

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logging.getLogger('boto3').setLevel(logging.CRITICAL)
logging.getLogger('botocore').setLevel(logging.CRITICAL)
logging.getLogger('s3transfer').setLevel(logging.CRITICAL)
logging.getLogger('urllib3').setLevel(logging.CRITICAL)

S3_DST_ACCESS_KEY_ID        = os.environ['S3_DST_ACCESS_KEY_ID']
S3_DST_SECRET_ACCESS_KEY    = os.environ['S3_DST_SECRET_ACCESS_KEY']
S3_REGION_NAME              = os.environ['S3_REGION_NAME']
SLACK_WEBHOOK               = os.environ['SLACK_WEBHOOK']
S3_DST_BUCKET_LOCATION      = os.environ['S3_DST_BUCKET_LOCATION']
#S3_DST_KEY_PREFIX           = os.environ['S3_DST_KEY_PREFIX']
S3_SRC_BUCKET_NAME          = os.environ['S3_SRC_BUCKET_NAME']
S3_SRC_KEY_PREFIX           = os.environ['S3_SRC_KEY_PREFIX']
BASE_PATH                   = '/NATS/scripts'
LOG_SUFFIX = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10)) + ".log"
LOG_FILE                = '/NATS/log/nats_hist_batch_upload' + LOG_SUFFIX
CSV_SUFFIX = S3_SRC_KEY_PREFIX.split('/')[-1]

def batch_check(myfile):
        try:
            file_name = unquote(myfile.split('/')[-1])
            download_path = '{0}{1}'.format(BASE_PATH,file_name)
        except:
            raise
        return os.path.isfile(download_path)

def build_new_fpl_json(input_json):
    """Given an input FPL dict
    Strip out the non x400message key and add all its subkeys
    as top level keys of a new dict

    Args:
    input_json - dict

    Returns:
    Dict
    """
    new_json = {}
    for key in input_json.keys():
        if key.lower() == 'x400message':
            new_json[key] = json.dumps(input_json[key])
        else:
            for sub_key in input_json[key]:
                new_json[sub_key] = input_json[key][sub_key]
            new_json['MessageType'] = key
    new_json['messageReceievedTime'] = input_json['X400Message']['envelope']['messageDeliveryTime']
    return new_json

def extract_message_received_time(input_json):
    """Extract the departure date from the EOBD field
    and return as datestring in the form 'YYYY-MM-DD'
    """
    date_str = input_json['messageReceievedTime']
    return f'msg_date=20{date_str[0:2]}-{date_str[2:4]}-{date_str[4:6]}'

def upload_file_s3(file_location, partition_str):
    """Uploads file to s3"""
    try:
        #logger.info('Uploading {0}'.format(file_location))
        #session = boto3.Session(profile_name=PROFILE)
        boto_s3_session = boto3.Session(
            aws_access_key_id=S3_DST_ACCESS_KEY_ID,
            aws_secret_access_key=S3_DST_SECRET_ACCESS_KEY,
            region_name=S3_REGION_NAME
        )
        s3_conn = boto_s3_session.resource('s3')
        file_name = file_location.split('/')[-1]
        bucket = S3_DST_BUCKET_LOCATION.split('/')[0]
        output_path = '/'.join(S3_DST_BUCKET_LOCATION.split('/')[1:]) + '/' + partition_str
        if os.path.getsize(file_location) != 0:
            s3_conn.Bucket(bucket).upload_file(file_location, '{0}/{1}'.format(output_path, file_name))
            #logger.info('Upload complete')
        else:
            logger.warning('Empty file, skipping upload')
    except Exception as e:
        logger.critical('Failed to upload')
        logger.critical(e)
        raise

def process_fpl(file_name1):
    file_name = file_name1.split('/')[-1]
    with open(f'{BASE_PATH}/{file_name}', 'r') as f:
        data = f.read()

    json_data = json.loads(data)
    new_json = build_new_fpl_json(json_data)
    new_json['filename'] = file_name
    new_json['entirejson'] = json_data
    partition_str = extract_message_received_time(new_json)

    with open(f'/{BASE_PATH}/parsed_{file_name}', 'w') as new_f:
        new_f.write(json.dumps(new_json))
    upload_file_s3(f'/{BASE_PATH}/parsed_{file_name}', partition_str)
    # Delete file_name and parsed_{file_name}
    if os.path.exists(f'/{BASE_PATH}/parsed_{file_name}'):
        os.remove(f'/{BASE_PATH}/parsed_{file_name}')
        os.remove(f'/{BASE_PATH}/{file_name}')
    return {'partition': partition_str, 'file_name': f'parsed_{file_name}'}

def get_batch_data(csv_fname):
    with open(csv_fname, "r") as batch_files:
        for batch_file in csv.reader(batch_files):
            yield batch_file

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
    logger.info('Starting Upload of S3 Files')
    filename = f'{BASE_PATH}/batchfile{CSV_SUFFIX}.csv'

    #loop. run till there are no READY files in batch_status_dict.
    batch_status_dict = {}
    while True:
        batch = iter(get_batch_data(filename))
        # Check only for batches that are not marked DONE or INPROGRESS when dictionary is not empty
        continue_flag=False
        #for key,val in json_data['Dict'].items():
        #Below for loop should run once for each batch before the batch is retried.
        for row in batch:
            try:
                if(bool(batch_status_dict)):
                # Move Pending ones to READY if all files are downloaded.
                    if(batch_status_dict[row[0]][1] == "PENDING"):
                        file_list=[]
                        for fname in eval(row[1]):
                            file_list.append(batch_check(fname))
                            # Batches that are NOT DONE OR INPROGRESS.
                        if(all(file_list)):
                            print(f'{row[0]} is READY with {len(file_list)} files' )
                            batch_status_dict[row[0]] = (eval(row[1]),'READY')
                        else:
                            continue
                else:
                    file_list=[]
                    for fname in eval(row[1]):
                        file_list.append(batch_check(fname))
                    # Batches that are NOT DONE OR INPROGRESS.
                    if(all(file_list)):
                        print(f'{row[0]} is READY with {len(file_list)} files' )
                        batch_status_dict[row[0]] = (eval(row[1]),'READY')
                    else:
                        batch_status_dict[row[0]] = (eval(row[1]),'PENDING')
                        print(f'{row[0]} Getting Prepared')

            except KeyError:
                file_list=[]
                for fname in eval(row[1]):
                    file_list.append(batch_check(fname))
                if(all(file_list)):
                    print(f'{row[0]} is READY with {len(file_list)} files' )
                    batch_status_dict[row[0]] = (eval(row[1]),'READY')
                else:
                    batch_status_dict[row[0]] = (eval(row[1]),'PENDING')
                    print(f'{row[0]} Getting Prepared')

        try:

            for key,val in batch_status_dict.items():
            #with concurrent.futures.ProcessPoolExecutor() as executor:
                if(val[1]=='READY'):
                    #batch_status_dict[key] = (val[0],'INPROGRESS')
                    logger.info('******BATCH INPROGRESS*******: {0}'.format(key))
                    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as executor:
                        executor.map(process_fpl,val[0])
                    batch_status_dict[key] = (val[0],'DONE')
                    logger.info('******BATCH DONE*******: {0}'.format(key))
                else:
                    pass
                    #No batches READY. They can be either DONE or PENDING or INPROGRESS
                    #You can't exit if there are batches in PENDING or INPROGRESS
                    #If you have only batches in PENDING. Wait for 300 seconds and exit
                    #after you check for signal from Download process completion or failure.

        except:
            logger.error("Failure Uploading files to S3")
            logger.exception(str(err))
            error = str(err)
            send_message_to_slack(error)

        finally:
            for k,v in batch_status_dict.items():
                if isinstance(v, tuple) and len(v)>1:
                    print(f'{k} status is {v[1]} ')
                    #if batch is DONE. Write to a file and  pop out the key
                    if(v[1]=='DONE'):
                        pass
                    elif(v[1]=='INPROGRESS'):
                        continue_flag=True
                    elif(v[1]=='PENDING'):
                        continue_flag=True
                    else:
                        pass

        if(continue_flag):
            continue
        else:
            break

    print("-----FINAL REPORT-------")
    for k,v in batch_status_dict.items():
        if isinstance(v, tuple) and len(v)>1:
            print(f'{k} status is {v[1]} ')

    print("-----Processing Time of Upload-------")
    print(datetime.now() - startTime)

if __name__ == '__main__':
    main()
