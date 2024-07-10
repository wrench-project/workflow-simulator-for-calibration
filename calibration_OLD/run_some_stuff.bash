#!/usr/bin/bash

NODES="-cn 4 -sn 4 "
CPUWORKS="-cc 1000 -sc 1000 "
DATAFOOTPRINTS="-cd 0 -sd 0 "

for TIMEOUT in 1 5 10 30 300; do

	WORKFLOW=seismology
	EVALUATE_SET="-st 1030"
	for ARCH in haswell skylake cascadelake; do
	
		CALIBRATE_SET="-ct 103 -ct 206 -ct 515"
		OUTPUT_FILE="test_output_${WORKFLOW}_${ARCH}_103_206_515_timeout=$TIMEOUT.json"
		python3 ./calibration/experiment_vary_tasks.py -i ~/JSONS -o $OUTPUT_FILE -c ./calibration/config.json  -ca $ARCH  -cw $WORKFLOW -sa $ARCH -sw $WORKFLOW $CALIBRATE_SET $EVALUATE_SET --keep-exp-directory $NODES $CPUWORKS $DATAFOOTPRINTS -t $TIMEOUT
	done
	
	
	WORKFLOW=genome
	EVALUATE_SET="-st 540"
	for ARCH in haswell skylake cascadelake; do
	
		CALIBRATE_SET="-ct 54 -ct 108 -ct 270"
		OUTPUT_FILE="test_output_${WORKFLOW}_${ARCH}_54_108_270_timeout=$TIMEOUT.json"
		python3 ./calibration/experiment_vary_tasks.py -i ~/JSONS -o $OUTPUT_FILE -c ./calibration/config.json  -ca $ARCH  -cw $WORKFLOW -sa $ARCH -sw $WORKFLOW $CALIBRATE_SET $EVALUATE_SET --keep-exp-directory $NODES $CPUWORKS $DATAFOOTPRINTS -t $TIMEOUT
	done
	
	WORKFLOW=montage
	EVALUATE_SET="-st 600"
	for ARCH in haswell skylake cascadelake; do
	
		CALIBRATE_SET="-ct 60 -ct 120 -ct 300"
		OUTPUT_FILE="test_output_${WORKFLOW}_${ARCH}_60_120_300_timeout=$TIMEOUT.json"
		python3 ./calibration/experiment_vary_tasks.py -i ~/JSONS -o $OUTPUT_FILE -c ./calibration/config.json  -ca $ARCH  -cw $WORKFLOW -sa $ARCH -sw $WORKFLOW $CALIBRATE_SET $EVALUATE_SET --keep-exp-directory $NODES $CPUWORKS $DATAFOOTPRINTS -t $TIMEOUT
	done	

done	




