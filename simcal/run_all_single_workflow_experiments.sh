#!/bin/bash

WORKFLOWS="chain cycles epigenomics forkjoin genome montage seismology soykb"
ARCHITECTURES="haswell skylake cascadelake"

TIMELIMIT=600

for workflow in $WORKFLOWS; do
        for architecture in $ARCHITECTURES; do
                python3 ./run_single_workflow_experiments.py -wd ../../JSONS -wn $workflow -ar $architecture -al random -tl $TIMELIMIT -th 48 -lf relative_average_error -cs htcondor_bare_metal -ss submit_and_compute_hosts  -ns one_and_then_many_links -cn CCskylake
        done
done

