#!/usr/bin/env python3

import pickle
import json
import argparse

import pickle
import json
import os

def pickle_to_json(pickle_path):
	# Load data from the pickle file
	with open(pickle_path, 'rb') as f:
		data = pickle.load(f)
	
	# Convert the data to JSON-compatible format
	json_data = recursive_to_dict(data)
	
	return json_data

def recursive_to_dict(data):
    # Handle dictionaries
    if isinstance(data, dict):
        return {k: recursive_to_dict(v) for k, v in data.items()}
    
    # Handle lists and tuples
    elif isinstance(data, (list, tuple)):
        return [recursive_to_dict(item) for item in data]
    
    # Handle sets (convert to list)
    elif isinstance(data, set):
        return [recursive_to_dict(item) for item in data]
    
    # Handle custom objects (convert to dict)
    elif hasattr(data, '__dict__'):
        return {k: recursive_to_dict(v) for k, v in data.__dict__.items() if not callable(v) and not k.startswith('__')}
    
    # Ignore functions and other callable objects
    elif callable(data):
        return None
    
    # For other types (ints, floats, strings, bools, None, etc.)
    else:
        return data



# Set up command-line argument parsing
parser = argparse.ArgumentParser(
	description="Convert a pickle file to a pretty-formatted JSON file.",
	epilog="Example: ./convert_pickle_to_json.py input.pkl output.json"
)
parser.add_argument('pickle_input', help="Path to the input pickle file.")
parser.add_argument('json_output', nargs='?',help="Path to the output JSON file.",default="")

# If no arguments are passed, print help
#if len(parser.parse_args()) == 0:
#	parser.print_help()

args = parser.parse_args()

# Load pickle file
data=pickle_to_json(args.pickle_input)
# Write data to a pretty-formatted JSON file
if args.json_output:
	with open(args.json_output, 'w') as f:
		json.dump(data, f, indent=4)
		print(f"Pickle file '{args.pickle_input}' has been converted to JSON and saved as '{args.json_output}'.")
else:
	print(json.dumps(data, indent=4))