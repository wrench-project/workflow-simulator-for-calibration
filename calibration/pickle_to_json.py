#!/usr/bin/env python3

import pickle
import json
import argparse

# Set up command-line argument parsing
parser = argparse.ArgumentParser(
    description="Convert a pickle file to a pretty-formatted JSON file.",
    epilog="Example: ./convert_pickle_to_json.py input.pkl output.json"
)
parser.add_argument('pickle_input', help="Path to the input pickle file.")
parser.add_argument('json_output', help="Path to the output JSON file.")

# If no arguments are passed, print help
#if len(parser.parse_args()) == 0:
#    parser.print_help()

args = parser.parse_args()

# Load pickle file
with open(args.pickle_input, 'rb') as f:
    data = pickle.load(f)

# Write data to a pretty-formatted JSON file
#with open(args.json_output, 'w') as f:
#    json.dump(data, f, indent=4)
print(data)
print(f"Pickle file '{args.pickle_input}' has been converted to JSON and saved as '{args.json_output}'.")
