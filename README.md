# dq-nats-historical-processing

[![Docker Repository on Quay](https://quay.io/repository/ukhomeofficedigital/dq-nats-sftp-python/status "Docker Repository on Quay")](https://quay.io/repository/ukhomeofficedigital/dq-nats-sftp-python)

A collection of Docker containers running a data pipeline.
Tasks include:
- Go through the S3 LOCATION provided and prepare a list of batch files.
- Download the batch files from S3 (NATS ARCHIVE)
- Process the downloaded S3 files, transform and AWS S3 PUT files to an S3 bucket (NATS INTERNAL)

## Dependencies

- Docker
- Python3.7
- Drone
- AWS CLI
- AWS Keys with PUT access to S3
- AWS Keys with GET access from S3
- Kubernetes

## Structure

- **app/**
  - *Dockerfile*: describe what is installed in the container and the Python file that needs to run
  - *docker-entrypoint.sh*: bash scripts running at container startup
  - *packages.txt*: Python custom Modules
  - **bin/**
    - *run_nats.sh*: Bash script runtime
  - **scripts/**
    - *prepare_batch_csv.py*: Python3.7 script running within the container
    - *download_batchfiles.py*: Python3.7 script running within the container
    - *upload_batchfiles.py*: Python3.7 script running within the container
- **kube/**
  - *job.yml*: describe a Kubernetes POD job
  - *pvc.yml*: declare a Persistent Volume in Kubernetes
  - *secret.yml*: list the Drone secrets passed to the containers during deployment  
- *.drone.yml*: CI deployment configuration
- *LICENSE*: MIT license file
- *README.md*: readme file

## Data flow

- *prepare_batch_csv.py* LIST files from S3
- *download_batchfiles.py* GET files from S3
- *upload_batchfiles.py* PUT files to S3

## Drone secrets

Environmental variables are set in Drone based on secrets listed in the *.drone.yml* file and they are passed to Kubernetes as required.

## Secrets

The script will require the following variables passed in at runtime.

|Name|Value|Required|Description|
| --- |:---:| :---:| --- |
| BATCH_SIZE | 300 | True | Size of the batch|
| S3_SRC_BUCKET_NAME|  Input s3-bucket-name| True | S3 bucket name|
| S3_DST_BUCKET_LOCATION | Output s3-bucket-location | True | S3 bucket location |
| S3_SRC_KEY_PREFIX | prefix | True | S3 folder name |
| S3_SRC_ACCESS_KEY_ID | ABCD | True | AWS access key ID |
| S3_DST_ACCESS_KEY_ID | ABCD | True | AWS access key ID |
| S3_SRC_SECRET_ACCESS_KEY | abcdb1234 | True | AWS Secret access key |
| S3_DST_SECRET_ACCESS_KEY | abcdb1234 | True | AWS Secret access key |
| S3_REGION_NAME | eu-west-2 | True | AWS Region Name |
| SLACK_WEBHOOK | https://hooks.slack.com/services/ABCDE12345 | True | Slack Webhook URL |

- Components:
  - NATS Python container
