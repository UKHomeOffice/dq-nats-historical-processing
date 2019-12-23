#!/bin/ksh
alias echo='echo $(date)'
echo started
ts=$(date +%Y%m%d%H%M%S)
python3 prepare_batch_csv.py > prepare_batch${ts}_$$_${RANDOM}.txt 2> prepare_batch${ts}_$$_${RANDOM}.log
python3 download_batchfiles.py > download${ts}_$$_${RANDOM}.txt 2> download${ts}_$$_${RANDOM}.log &
python3 upload_batchfiles.py.py
echo Ended
