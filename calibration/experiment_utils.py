#!/usr/bin/env python3

import os
import sys
import subprocess
import json
import time
from argparse import ArgumentParser

import workflow_queries as wfq

# User-defined constants
wf_arch  = ["haswell", "skylake", "cascadelake"]
wf_names = ["seismology", "montage", "genome", "soykb",
            "cycles", "epigenomics", "bwa", 
            "chain", "forkjoin"]

workflow_sim = "workflow-simulator-for-calibration"
calibrate_py = "calibration/calibrate.py"

def find_exp_hash(stdout):
    if '===============' in stdout:
        return stdout.split('===============')[1].split('===============')[0].strip()
    else:
        return 'ERROR'

# Returns a list of 'exp-*'directories
def get_exp_list():
    directories = []

    # Iterate over items in the current directory
    for item in os.listdir(os.getcwd()):
        # Check if the item is a directory and starts with 'exp-'
        if os.path.isdir(os.path.join(item)) and item.startswith('exp-'):
            directories.append(item)

    return directories

# Returns a list of items that are in list2 but not in list1
def compare_lists(list1, list2):
    return [item for item in list2 if item not in list1]

def parse_arguments(args):
    parser = ArgumentParser()

    parser.add_argument("-i", "--input_dir", required=True,
                        action='append',
                        help="Input directory containing workflow JSON files (only one)")

    parser.add_argument("-o", "--output_file", required=True,
                        action='append',
                        help="Output file name, not including '.json' (only one)")

    parser.add_argument("-c", "--config_json", required=True,
                        action='append',
                        help="Config file, including '.json' extension (only one)")

    parser.add_argument('-it', '--iter', action='store',
                        type=int, default=500,
                        help='Maximum number of iterations in calibration (default: 500)')

    parser.add_argument('-t', '--timeout', action='store',
                        type=int, default=60,
                        help='Timeout in seconds for calibration (default: 60s)')

    parser.add_argument("-k", "--keep-exp-directory", action='store_true',
                        help="Keep 'exp-*' directories after calibration (default: false)")

    # Calibration arguments
    parser.add_argument("-ca", "--calibrate_architecture", required=False, choices=wf_arch,
                        action='extend', nargs='+',
                        help="<" + "|".join(wf_arch) + "> (zero or more)")

    parser.add_argument("-cw", "--calibrate_workflow_name", required=False, choices=wf_names,
                        action='extend', nargs='+',
                        help="<" + "|".join(wf_names) + "> (zero or more)")

    parser.add_argument("-cn", "--calibrate_num_compute_nodes", type=int, required=False,
                        action='extend', nargs='+',
                        help="<# of compute nodes> (zero or more)")

    parser.add_argument("-cc", "--calibrate_cpu_work", type=int, required=False,
                        nargs='+',
                        action='extend',
                        help="<CPU work value> (zero or more)")

    parser.add_argument("-cf", "--calibrate_cpu_fraction", type=float, required=False,
                        nargs='+',
                        action='extend',
                        help="<CPU fraction> (zero or more)")

    parser.add_argument("-cd", "--calibrate_data_footprint", type=int, required=False,
                        nargs='+',
                        action='extend',
                        help="<data footprint in bytes> (zero or more)")
    
    parser.add_argument("-ct", "--calibrate_num_tasks", type=int, required=False,
                       nargs='+',
                       action='extend',
                       help="<# of tasks in workflow> (zero or more)")

    # Simulation arguments
    parser.add_argument("-sa", "--simulate_architecture", required=False, choices=wf_arch,
                        action='extend', nargs='+',
                        help="<" + "|".join(wf_arch) + "> (zero or more)")

    parser.add_argument("-sw", "--simulate_workflow_name", required=False, choices=wf_names,
                        action='extend', nargs='+',
                        help="<" + "|".join(wf_names) + "> (zero or more)")

    parser.add_argument("-sn", "--simulate_num_compute_nodes", type=int, required=False,
                        action='extend', nargs='+',
                        help="<# of compute nodes> (zero or more)")

    parser.add_argument("-sc", "--simulate_cpu_work", type=int, required=False,
                        nargs='+',
                        action='extend',
                        help="<CPU work value> (zero or more)")

    parser.add_argument("-sf", "--simulate_cpu_fraction", type=float, required=False,
                        nargs='+',
                        action='extend',
                        help="<CPU fraction> (zero or more)")

    parser.add_argument("-sd", "--simulate_data_footprint", type=int, required=False,
                        nargs='+',
                        action='extend',
                        help="<data footprint in bytes> (zero or more)")
    
    parser.add_argument("-st", "--simulate_num_tasks", type=int, required=False,
                       nargs='+',
                       action='extend',
                       help="<# of tasks in workflow> (zero or more)")

    parsed_args = parser.parse_args(args[1:])
    config = {}

    # Input workflow dir
    input_dir_values = parsed_args.input_dir
    if len(input_dir_values) > 1:
        sys.stderr.write("Error: a single -i/--input_dir argument should be specified\n")
        sys.exit(1)
    if not os.path.isdir(input_dir_values[0]):
        sys.stderr.write("Error: input directory '" + input_dir_values[0] + "' does not exist\n")
        sys.exit(1)
    config["input_dir"] = input_dir_values[0]

    # Output File
    output_file_values = parsed_args.output_file
    if len(output_file_values) > 1:
        sys.stderr.write("Error: a single -o/--output_file argument should be specified\n")
        sys.exit(1)
    config["output_file"] = output_file_values[0]

    # Config JSON file
    config_json_values = parsed_args.config_json
    if len(config_json_values) > 1:
        sys.stderr.write("Error: a single -c/--config_json argument should be specified\n")
        sys.exit(1)
    if not os.path.isfile(config_json_values[0]):
        sys.stderr.write("Error: config JSON file '" + config_json_values[0] + "' does not exist\n")
        sys.exit(1)
    config["config_json"] = config_json_values[0]

    config["num_iter"] = parsed_args.iter
    config["timeout"] = parsed_args.timeout
    config["keep_exp_dir"] = parsed_args.keep_exp_directory 

    # Calibration arguments
    # Architecture 
    if parsed_args.calibrate_architecture != None:
        config["calibrate_architecture"] = list(set(parsed_args.calibrate_architecture))

    # Workflow
    if parsed_args.calibrate_workflow_name != None:
        config["calibrate_workflow_name"] = list(set(parsed_args.calibrate_workflow_name))

    # Num compute nodes
    if parsed_args.calibrate_num_compute_nodes != None:
        config["calibrate_node"] = list(set(parsed_args.calibrate_num_compute_nodes))

    # CPU works
    if parsed_args.calibrate_cpu_work != None:
        config["calibrate_cpu_work"] = list(set(parsed_args.calibrate_cpu_work))

    # CPU fractions
    if parsed_args.calibrate_cpu_fraction != None:
        config["calibrate_cpu_frac"] = list(set(parsed_args.calibrate_cpu_fraction))

    # Data footprints
    if parsed_args.calibrate_data_footprint != None:
        config["calibrate_data_fp"] = list(set(parsed_args.calibrate_data_footprint))

    # Tasks
    if parsed_args.calibrate_num_tasks != None:
        config["calibrate_num_tasks"] = list(set(parsed_args.calibrate_num_tasks))

    # Simulation arguments
    # Architecture 
    if parsed_args.simulate_architecture != None:
        config["simulate_architecture"] = list(set(parsed_args.simulate_architecture))

    # Workflow
    if parsed_args.simulate_workflow_name != None:
        config["simulate_workflow_name"] = list(set(parsed_args.simulate_workflow_name))

    # Num compute nodes
    if parsed_args.simulate_num_compute_nodes != None:
        config["simulate_node"] = list(set(parsed_args.simulate_num_compute_nodes))

    # CPU works
    if parsed_args.simulate_cpu_work != None:
        config["simulate_cpu_work"] = list(set(parsed_args.simulate_cpu_work))

    # CPU fractions
    if parsed_args.simulate_cpu_fraction != None:
        config["simulate_cpu_frac"] = list(set(parsed_args.simulate_cpu_fraction))

    # Data footprints
    if parsed_args.simulate_data_footprint != None:
        config["simulate_data_fp"] = list(set(parsed_args.simulate_data_footprint))

    # Tasks
    if parsed_args.simulate_num_tasks != None:
        config["simulate_num_tasks"] = list(set(parsed_args.simulate_num_tasks))

    return config

# Returns a sorted list of workflows filtered based on config
def parse_calibrate_args(config, debug=False):
    wf_list = os.listdir(config['input_dir'])
    if debug == True:
        print(wf_list)

    # Filter wf_list into calibrate_list
    calibrate_list = wf_list
    if "calibrate_architecture" in config:
        if debug == True:
            print(f"calibrate_architecture = {config['calibrate_architecture']}")
        calibrate_list = wfq.filter_archs(calibrate_list, config['calibrate_architecture'])
    if "calibrate_workflow_name" in config:
        if debug == True:
            print(f"calibrate_workflow_name = {config['calibrate_workflow_name']}")
        calibrate_list = wfq.filter_names(calibrate_list, config['calibrate_workflow_name'])
    if "calibrate_node" in config:
        if debug == True:
            print(f"calibrate_node = {config['calibrate_node']}")
        calibrate_list = wfq.filter_nodes(calibrate_list, config['calibrate_node'])
    if "calibrate_cpu_work" in config:
        if debug == True:
            print(f"calibrate_cpu_work = {config['calibrate_cpu_work']}")
        calibrate_list = wfq.filter_cpu_works(calibrate_list, config['calibrate_cpu_work'])
    if "calibrate_cpu_frac" in config:
        if debug == True:
            print(f"calibrate_cpu_frac = {config['calibrate_cpu_frac']}")
        calibrate_list = wfq.filter_cpu_fracs(calibrate_list, config['calibrate_cpu_frac'])
    if "calibrate_data_fp" in config:
        if debug == True:
            print(f"calibrate_data_fp = {config['calibrate_data_fp']}")
        calibrate_list = wfq.filter_data_footprints(calibrate_list, config['calibrate_data_fp'])
    if "calibrate_num_tasks" in config:
        if debug == True:
            print(f"calibrate_num_tasks = {config['calibrate_num_tasks']}")
        calibrate_list = wfq.filter_tasks(calibrate_list, config['calibrate_num_tasks'])
    
    calibrate_list.sort()
    if debug == True:
        print(f"calibrate_list = {calibrate_list}")
    return calibrate_list

# Returns a sorted list of workflows filtered based on config
def parse_simulate_args(config, debug=False):
    wf_list = os.listdir(config['input_dir'])
    if debug == True:
        print(wf_list)

    # Filter wf_list into simulate_list
    simulate_list = wf_list
    if "simulate_architecture" in config:
        if debug == True:
            print(f"simulate_architecture = {config['simulate_architecture']}")
        simulate_list = wfq.filter_archs(simulate_list, config['simulate_architecture'])
    if "simulate_workflow_name" in config:
        if debug == True:
            print(f"simulate_workflow_name = {config['simulate_workflow_name']}")
        simulate_list = wfq.filter_names(simulate_list, config['simulate_workflow_name'])
    if "simulate_node" in config:
        if debug == True:
            print(f"simulate_node = {config['simulate_node']}")
        simulate_list = wfq.filter_nodes(simulate_list, config['simulate_node'])
    if "simulate_cpu_work" in config:
        if debug == True:
            print(f"simulate_cpu_work = {config['simulate_cpu_work']}")
        simulate_list = wfq.filter_cpu_works(simulate_list, config['simulate_cpu_work'])
    if "simulate_cpu_frac" in config:
        if debug == True:
            print(f"simulate_cpu_frac = {config['simulate_cpu_frac']}")
        simulate_list = wfq.filter_cpu_fracs(simulate_list, config['simulate_cpu_frac'])
    if "simulate_data_fp" in config:
        if debug == True:
            print(f"simulate_data_fp = {config['simulate_data_fp']}")
        simulate_list = wfq.filter_data_footprints(simulate_list, config['simulate_data_fp'])
    if "simulate_num_tasks" in config:
        if debug == True:
            print(f"simulate_num_tasks = {config['simulate_num_tasks']}")
        simulate_list = wfq.filter_tasks(simulate_list, config['simulate_num_tasks'])
    
    simulate_list.sort()
    if debug == True:
        print(f"simulate_list = {simulate_list}")
    return simulate_list

# Calibrates on workflows in wf_list
# Returns the exp_hash value, i.e., directory created by calibration containing 'best-bo.json' and 'best-rs.json'
    # wf_list       = list of workflow file names to calibrate
    # dir_wf        = directory containing workflows in wf_list
    # config_json   = config JSON file
    # num_iter      = maximum number of iterations
    # timeout       = maximum number of seconds per calibration (i.e., with --all, we expect roughly 2*timeout total seconds)
    # until_success = if true, will attempt to calibrate until sucess
    # max_attempts  =  if until_sucess if false, the maximum number of attempts to calibrate
    # debug         = if true, prints debug statements
def calibrate(wf_list, dir_wf, config_json, num_iter, timeout, until_success=True, max_attempts=20, debug=True):
    # Convert wf_list into a single string of workflows
    wf_string = ""
    for wf in wf_list:
        wf_string += str(os.path.abspath(dir_wf)) + '/' + str(wf) + ' '
    wf_string = wf_string.strip()

    # Command string
    cmd_string = str(os.path.abspath(calibrate_py)) + ' --config ' + str(os.path.abspath(config_json)) + ' --iter ' + str(num_iter) + ' --deephyper-timeout ' + str(timeout) + ' --all --workflows ' + wf_string

    # Attempt to calibrate on workflows, until success or max_attempts
    full_timeout = 2*timeout + 20      # total time to consider a process as 'failed' (allow an overhead of 20s)
    attempt = 0
    while until_success or attempt <= max_attempts:
        try:
            calibrate_run = subprocess.run(cmd_string, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8", shell=True, timeout=full_timeout)

            exp_hash = find_exp_hash(calibrate_run.stdout)

            # Rerun if errors are found
            # Otherwise return exp_hash
            if "deephyper.core.exceptions.SearchTerminationError" in calibrate_run.stdout:
                if debug == True:
                    print(f"Attempt {attempt}: 'deephyper.core.exceptions.SearchTerminationError' detected... Retrying...")
            elif exp_hash == "ERROR":
                if debug == True:
                    print(f"Attempt {attempt}: Error during calibration... Retrying...")
            else:
                if debug == True:
                    print(f"Attempt {attempt}: Success!")
                return exp_hash
        except subprocess.TimeoutExpired:
            if debug == True:
                print(f"Attempt {attempt}: Calibration took too long... Retrying...")

        attempt += 1

# Simulates wf using calibrated values from exp_json
    # wf       = workflow to simulate
    # dir_wf   = directory containing workflow wf
    # exp_json = JSON file from calibration (e.g., best_bo.json or best_rs.json)
def simluate(wf, dir_wf, exp_json):
    simulate_run = subprocess.run([workflow_sim, exp_json, str(os.path.abspath(dir_wf)) + '/' + str(wf)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8")
    return simulate_run.stdout