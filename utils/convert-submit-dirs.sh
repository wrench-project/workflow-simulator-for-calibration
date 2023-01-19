#!/usr/bin/env bash
###############################################################################
#
# Author: Loic Pottier <pottier1@llnl.gov>
#
# This script takes a directory containing Pegasus submit dirs and convert all
# Pegasus workflows into JSON representations compatible with WRENCH
# The $DATA_ROOT_DIR must look like:
# $DATA_ROOT_DIR/
#   level1/
#     level2/
#       level3/
#         ....
#           level_DEPTH/ -> the pegasus submit dir
###############################################################################

EXE="pegasus-submit-to-json.py"
PYTHON="python3"
DATA_ROOT_DIR="../../data"
DEPTH="4"

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

i=1
k=1
# We need that dependency
${PYTHON} -m pip --disable-pip-version-check -q install wfcommons

# Dev mode (useful to get latest bugfixes..)
if true; then
  echo -n "Installing wfcommons from master branch ..."
  if [ ! -d "wfcommons" ]; then 
      git clone --quiet git@github.com:wfcommons/wfcommons.git
  fi
  if ${PYTHON} -m pip install --disable-pip-version-check -q -e wfcommons ; then
      echo -e " [ ${GREEN}OK${NC} ]"
  else
      echo -e " [${RED}FAIL${NC}]"
      exit
  fi
fi

# Clean previous runs
rm -rf *.err

echo "=================================================="
SECONDS=0
for workflow in $(find $DATA_ROOT_DIR -maxdepth $DEPTH -mindepth $DEPTH -type d); do
    json_output="$(basename $workflow).json"
    if [ ! -f "$json_output" ]; then
        echo -en "[$i] Converting $workflow -> $json_output ..."
        if  ${PYTHON} ${EXE} -i $workflow -o $json_output 2> $(basename $workflow).err ; then
          echo -e " [ ${GREEN}OK${NC} ]"
          let k++
        else
          echo -e " [${RED}FAIL${NC}]"
        fi
    else
        echo "[$i] Skipping $json_output ... (already exists)."
    fi
    let i++
done
# Cleanup err log which are empty
find *.err -size 0 -delete
rm -rf .pegasus-parser*

echo "=================================================="
echo "Converted $k/$i directories in $SECONDS seconds".
echo "=================================================="
