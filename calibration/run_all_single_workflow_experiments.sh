#!/bin/bash

if [ "$#" -ne 6 ]; then
    echo "Usage: $0 <grid | random | gradient | skopt.gp | skopt.et | skopt.rf | skopt.gbrt> <time limit in seconds> <number of threads to use> <workflows> <architectures> <locale>"
    exit 1
fi

ALGORITHM="$1"
TIME_LIMIT="$2"
NUM_THREADS="$3"

WORKFLOWS="$4"
#WORKFLOWS="chain cycles epigenomics forkjoin genome montage seismology soykb"
#WORKFLOWS="bwa"

ARCHITECTURES="$5"
#ARCHITECTURES="haswell skylake cascadelake"
#ARCHITECTURES="cascadelake"

LOCALE="$6"
export DYLD_LIBRARY_PATH=/usr/local/lib


for workflow in $WORKFLOWS; do
	for architecture in $ARCHITECTURES; do
		echo "* Experiment: $workflow on $architecture"
		python3 ./run_single_workflow_experiments.py -wd ../../JSONS -wn $workflow -ar $architecture -al $ALGORITHM -tl $TIME_LIMIT -th $NUM_THREADS -lf relative_average_error -cs htcondor_bare_metal -ss submit_and_compute_hosts  -ns one_and_then_many_links -cn $LOCALE
	done 
done

