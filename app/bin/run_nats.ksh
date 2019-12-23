#!/bin/ksh
alias echo='echo $(date)'
echo started
python3 s1_prepare_batch_csv_1.py > s1.txt 2> s1_errors.log 
python3 s2_download_batchfiles.py &
python3 script4_upload_s3_multiprocess_1.py
echo Ended
