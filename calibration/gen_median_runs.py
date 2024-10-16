#!/usr/bin/env python3
import argparse
import time
import sys
import os
import json
import shutil
from glob import glob
from datetime import timedelta
from Util import *
from itertools import groupby
from statistics import median

def group(flat):
    # Use a regular expression to split the string before the last part (repeat number)
    def split_key(s):
        return '-'.join(s.split('-')[0:7])

    # Sort the strings based on the non-repeat part
    sorted_strings = sorted(flat, key=split_key)
    
    # Group by the non-repeat part
    grouped_strings = [list(group) for _, group in groupby(sorted_strings, key=split_key)]
    
    return grouped_strings

def parse_command_line_arguments(program_name: str):
    epilog_string = ""

    parser = argparse.ArgumentParser(
        prog=program_name,
        description='Workflow simulator calibrator',
        epilog=epilog_string)
    try:
        parser.add_argument('-ts', '--training_set', required=True, type=str, nargs="+",
                            help='The list of json files to use for training')
        parser.add_argument('-d', '--destination_folder', required=True, type=str,
                            help='Folder to copy the selected JSON files with median makespan value')

        return vars(parser.parse_args()), parser, None

    except argparse.ArgumentError as error:
        return None, parser, error

def get_makespan(json_file):
    """Extract the 'makespan' value from the given JSON file."""
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
            return float(data["workflow"]["execution"]["makespanInSeconds"])
    except (json.JSONDecodeError, KeyError):
        sys.stderr.write(f"Error: Could not read or find 'makespan' in {json_file}\n")
        return None

def main():
    # Parse command-line arguments
    args, parser, error = parse_command_line_arguments(sys.argv[0])
    if not args:
        sys.stderr.write(f"Error: {error}\n")
        parser.print_usage()
        sys.exit(1)
    
    # Group the training set
    training_groups = group(args['training_set'])
    
    # Ensure destination folder exists
    destination_folder = args['destination_folder']
    if not os.path.exists(destination_folder):
        os.makedirs(destination_folder)

    for groupd in training_groups:
        makespan_values = []
        valid_files = []
        
        # Collect makespan values and valid json files
        for file in groupd:
            makespan = get_makespan(file)
            if makespan is not None:
                makespan_values.append(makespan)
                valid_files.append(file)
        
        if makespan_values:
            # Find the median makespan
            median_makespan = median(makespan_values)
            median_index = makespan_values.index(median_makespan)
            selected_file = valid_files[median_index]
            
            # Copy the selected file to the destination folder
            destination_path = os.path.join(destination_folder, os.path.basename(selected_file))
            shutil.copy(selected_file, destination_path)
            print(f"Copied {selected_file} to {destination_path}")

if __name__ == "__main__":
    main()
