#!/usr/bin/env python3

import pickle
import json
import argparse

import pickle
import json
import os
import re
_units={None:1,"":1,
"s":1,"ms":0.001,"us":0.000001,"ns":0.000000001,
"f":1,"Kf":1_000, "Mf":1_000_000,"Gf":1_000_000_000,
"Bps":1,"KBps":1_000,"MBps":1_000_000,"GBps":1_000_000_000,
"bps":1,"Kbps":1_000,"Mbps":1_000_000,"Gbps":1_000_000_000,
"b":1,"Kb":1_000,"Mb":1_000_000,"Gb":1_000_000_000,
"B":1,"KB":1_000,"MB":1_000_000,"GB":1_000_000_000}
def shrink(param):
	result = re.match(r"(\d+\.?\d*)([a-zA-Z]+)*", str(param)).groups()
	value=float(result[0])
	if result[1] is None:
		return str(value)
	if result[1]=="s":
		if value > 216000:
			return str(round(value/216000,2))+"d"
		elif value> 3600:
			return str(round(value/3600,2))+"h"
		elif value > 60:
			return str(round(value/60,2))+"m"
		elif value > .1:
			return str(round(value,2))+"s"
		elif value > 0.0001:
			return str(round(value/0.001,2))+"ms"
		elif value > 0.0000001:
			return str(round(value/0.000001,2))+"us"
		else:
			return str(round(value/0.000000001,2))+"ns"

	if(value>1_000_000_000_000):
		return f"{round(value/1_000_000_000_000,2)}T{result[1]}"
	if(value>1_000_000_000):
		return f"{round(value/1_000_000_000,2)}G{result[1]}"
	if(value>1_000_000):
		return f"{round(value/1_000_000,2)}M{result[1]}"
	if(value>1_000):
		return f"{round(value/1_000,2)}K{result[1]}"
	else:
		return f"{round(value,2)}{result[1]}"
def calibration_from_pickle(pickle_path,human):
	# Load data from the pickle file
	with open(pickle_path, 'rb') as f:
		data = pickle.load(f)
	
	# Convert the data to JSON-compatible format
	json_data = []
	for exp in data.experiments:
		calibration=exp.calibration
		if human:
			for key in calibration:
				calibration[key]=shrink(calibration[key])
		json_data.append(calibration)
	if len(data.experiments)==1:
		json_data=json_data[0]
	return json_data



# Set up command-line argument parsing
parser = argparse.ArgumentParser(
	description="Convert a pickle file to a pretty-formatted JSON file.",
	epilog="Example: ./convert_pickle_to_json.py input.pkl output.json"
)
parser.add_argument('pickle_input', help="Path to the input pickle file.")
parser.add_argument('json_output', nargs='?',help="Path to the output JSON file.",default="")
parser.add_argument("-H",'--human',help="Human readable",action="store_true")

# If no arguments are passed, print help
#if len(parser.parse_args()) == 0:
#	parser.print_help()

args = parser.parse_args()

# Load pickle file
data=calibration_from_pickle(args.pickle_input,args.human)
# Write data to a pretty-formatted JSON file
if args.json_output:
	with open(args.json_output, 'w') as f:
		json.dump(data, f, indent=4, default=lambda o: str(o))
		print(f"Pickle file '{args.pickle_input}' has been converted to JSON and saved as '{args.json_output}'.")
else:
	print(json.dumps(data, indent=4, default=lambda o: str(o)))