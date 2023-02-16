#!/usr/bin/env bash
###############################################################################
#
# Author: Loïc Pottier <pottier1@llnl.gov>
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
# This DIR structure will be cloned into OUTPUT
###############################################################################

usage() { 
  echo "Usage: $0 -d <path> [-o <output dir>]" 1>&2
  exit 1
}
EXE="pegasus-submit-to-json.py"
PYTHON="python3"
DEPTH="4"

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

i=1
k=1

while getopts ":d:o:" arg; do
  case "${arg}" in
    d)
      DATA_ROOT_DIR=${OPTARG}
      ;;
    o)
	  OUTPUT_DIR=${OPTARG}
	  ;;
    *)
      usage
      ;;
  esac
done

shift $((OPTIND-1))
if [ -z "${DATA_ROOT_DIR}" ]; then
  usage
fi
if [ -z "${OUTPUT_DIR}" ]; then
  OUTPUT_DIR=output
fi
echo -n "Directory: ${DATA_ROOT_DIR}"
if [ -d "$DATA_ROOT_DIR" ]; then
  echo -e " [ ${GREEN}OK${NC} ]"
else
  echo -ne " [${RED}FAIL${NC}]"
  echo -e "\t -> This directory does not exist."
  exit
fi
echo $OUTPUT_DIR
if [ ! -d "$(dirname "$OUTPUT_DIR")" ] ; then
	echo "$(dirname "$OUTPUT_DIR") does not exist"
	exit
fi
if [ $(find "$OUTPUT_DIR" -mindepth 1 -maxdepth 1 | wc -l) -ne 0 ]; then
	read -p "$OUTPUT_DIR is not empty, continue anyway (y/N)" choice
	case "$choice" in
	  y|Y )
		#continue
		;;
	  * )
		echo "Aborting."
		exit 0
		;;
	esac
fi
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
find $OUTPUT_DIR -name *.err -delete

echo "=================================================="
echo "Extracting any Tar balls"
SECONDS=0
for dirs in $(find "$DATA_ROOT_DIR" -maxdepth `echo $DEPTH-1|bc` -mindepth `echo $DEPTH-1|bc` -type d); do 
	pushd $dirs > /dev/null
	for workflow in $(find . -maxdepth 1 -type f -name "*.tar.gz"); do
		if [ ! -d `echo $workflow|sed "s/.tar.gz//"` ] ; then 
			mkdir `echo $workflow|sed "s/.tar.gz//"`
			echo Extracting $workflow
			tar -xzf $workflow  -C `echo $workflow|sed "s/.tar.gz//"` --strip-components 1
		fi
	done 
	popd > /dev/null
done

echo "=================================================="
echo "Converting..."
for workflow in $(find "$DATA_ROOT_DIR" -maxdepth $DEPTH -mindepth $DEPTH -type d); do
	RELATIVE=$(dirname $(realpath --relative-to="$DATA_ROOT_DIR" "$workflow"))
	mkdir -p "$OUTPUT_DIR/$RELATIVE"
	#pushd "$OUTPUT_DIR/$RELATIVE" > /dev/null
    json_output="$OUTPUT_DIR/$RELATIVE/$(basename $workflow).json"
    if [ ! -f "$json_output" ]; then
        echo -en "[$i] Converting $workflow -> $json_output ...\t"
        if  ${PYTHON} ${EXE} -i $workflow -o $json_output 2> "$OUTPUT_DIR/$RELATIVE/$(basename $workflow).err" ; then
          echo -e " [ ${GREEN}OK${NC} ]" | column -t -s $'\t'
          let k++
        else
          echo -e " [${RED}FAIL${NC}]" | column -t -s $'\t'
        fi
        
    else
        echo "[$i] Skipping $json_output ... (already exists)."
    fi
    let i++
    
	find . -name *.err -size 0 -delete
    #popd > /dev/null
    
done
# Cleanup err log which are empty
rm -rf .pegasus-parser*

echo "=================================================="
echo "Converted $k/$i directories in $SECONDS seconds".
echo "=================================================="
