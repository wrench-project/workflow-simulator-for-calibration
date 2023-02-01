#!/usr/bin/env bash
###############################################################################
#
# Author: Loïc Pottier <pottier1@llnl.gov>
#
###############################################################################

usage() { 
  echo "Usage: $0 [-d <dirpath of JSON workflows>] [-c <config file>]" 1>&2
  exit 1
}

EXE="calibrate.py"
PYTHON="python3"
ITER=300
#CORES=1 # Number of cores used per calibration (if not specified use all cores available

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

i=0

while getopts ":d:c:" arg; do
  case "${arg}" in
    d)
      JSON_DIR=${OPTARG}
      ;;
    c)
      CONFIG=${OPTARG}
      ;;
    *)
      usage
      ;;
  esac
done

shift $((OPTIND-1))
if [ -z "${JSON_DIR}" || -z "${CONFIG}" ]; then
  usage
fi

echo -n "Directory: ${JSON_DIR}"
if [ -d "$JSON_DIR" ]; then
  echo -e " [ ${GREEN}OK${NC} ]"
else
  echo -ne " [${RED}FAIL${NC}]"
  echo -e "\t -> This directory does not exist."
  exit
fi

echo -n "Configuration file: ${CONFIG}"
if [ -f "$CONFIG" ]; then
  echo -e " [ ${GREEN}OK${NC} ]"
else
  echo -ne " [${RED}FAIL${NC}]"
  echo -e "\t -> This file does not exist."
  exit
fi

# clean up potential older runs
rm -rf *.log

echo "=================================================="
WF=$(find $JSON_DIR -maxdepth 1 -mindepth 1 -type f -name '*.json')
NB_WF=$(echo $WF | wc -l | tr -d '[:blank:]')
echo "> Number of  workflows          = $NB_WF"
echo "> Number of iterations/workflow = $ITER"
echo "  > Early stopping              = No"
echo "> Config file used              = $CONFIG"
echo "> Cores                         = All available"

SECONDS=0
for workflow in $(find $JSON_DIR -maxdepth 1 -mindepth 1 -type f -name '*.json'); do
  wf=$(basename $workflow)
  filename="${wf%.*}"
  echo -en "[$((i+1))] Calibrating ${wf} ...\t"
  if ${PYTHON} ${EXE} --config $CONFIG --workflow $workflow --iter $ITER --all --no-early-stopping > $filename.log 2>&1 ; then
    echo -e " [ ${GREEN}OK${NC} ]" | column -t -s $'\t'
  else
    echo -e " [${RED}FAIL${NC}]" | column -t -s $'\t'
  fi
  let i++
done

echo "=================================================="
echo "Calibrated $i workflows in $SECONDS seconds".
echo "=================================================="
