#!/bin/sh
alias echo='echo $(date)'
echo started
ts=$(date +%Y%m%d%H%M%S)

python3 /NATS/scripts/prepare_batch_csv.py > /NATS/log/prepare_batch${ts}_$$_${RANDOM}_$(hostname).txt 2> /NATS/log/prepare_batch${ts}_$$_${RANDOM}_$(hostname).log
python3 /NATS/scripts/download_batchfiles.py > /NATS/log/download${ts}_$$_${RANDOM}_$(hostname).txt 2> /NATS/log/download${ts}_$$_${RANDOM}_$(hostname).log &
python3 /NATS/scripts/upload_batchfiles.py.py

echo Ended
