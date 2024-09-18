#!/bin/bash

if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <grid | random | gradient> <time limit in seconds> <number of threads to use>"
    exit 1
fi

ALGORITHM="$1"
TIME_LIMIT="$2"
NUM_THREADS="$3"

#WORKFLOWS_TRAIN="chain forkjoin"
WORKFLOWS_TRAIN="forkjoin"
#WORKFLOWS_EVAL="cycles epigenomics genome montage seismology soykb"
WORKFLOWS_EVAL="cycles"
#ARCHITECTURES="haswell skylake cascadelake"
ARCHITECTURES="icelake"

export DYLD_LIBRARY_PATH=/usr/local/lib


for workflow_train in $WORKFLOWS_TRAIN; do
	for workflow_eval in $WORKFLOWS_EVAL; do
        	for architecture in $ARCHITECTURES; do
            		echo "* Experiment: $workflow on $architecture"
	        		python3 ./run_workflow_generalization_experiments.py -wd ../../JSONS -wnt $workflow_train -wne $workflow_eval -ar $architecture -al $ALGORITHM -tl $TIME_LIMIT -th $NUM_THREADS -lf relative_average_error -cs htcondor_bare_metal -ss submit_and_compute_hosts  -ns one_and_then_many_links -cn CCskylake
        	done 
        done 
done

