#!/usr/bin/env python3

import os
import sys
import subprocess
import json
import time
import random
import string
from argparse import ArgumentParser
from collections import Counter

import workflow_queries as wfq

# User-defined constants
wf_arch  = ["haswell", "skylake", "cascadelake"]
wf_names = ["seismology", "montage", "genome", "soykb",
            "cycles", "epigenomics", "bwa", 
            "chain", "forkjoin"]

workflow_sim = "workflow-simulator-for-calibration"
calibrate_py = "calibration/calibrate.py"

# Generates a random string containing letters and numbers
def generate_random_string(length=32):
    characters = string.ascii_letters + string.digits
    random_prefix = ''.join(random.choice(characters) for _ in range(length))
    return random_prefix

# Initializes my_dict using outfile and creates the `run-*` directory
# Returns the name of the `run-*` directory
# Assumes my_dict is initially an empty dictionary
# Assumes outfile contains JSON for the experiment
def init_experiment(dir_wf, config_json, outfile, num_iter, timeout):
    my_dict = {}
    if os.path.exists(outfile):
        sys.stderr.write("Result file " + outfile + " already exists..")
        with open(outfile, "r") as fp:
            my_dict = json.load(fp)

            if my_dict["config"] != config_json:
                print(f"ERROR: Config files do not match! {my_dict['config']} vs. {config_json}")
                sys.exit(1)
            if my_dict["timeout_seconds"] != timeout:
                print(f"Timeout values do not match! {my_dict['timeout_seconds']} vs. {timeout}")
                sys.exit(1)
    else:
        my_dict["input_dir"]           = dir_wf
        my_dict["config"]              = config_json
        my_dict["num_iter"]            = num_iter
        my_dict["timeout_seconds"]     = timeout
        my_dict["experiments"]         = list()

    # Generate unique directory name
    my_dir = "run-" + generate_random_string()
    while os.path.isdir(my_dir):
        my_dir = "run-" + generate_random_string()

    # Create directory
    mkdir_proc = subprocess.run(["mkdir", my_dir], capture_output=True)
    while mkdir_proc.returncode != 0:
        mkdir_proc = subprocess.run(["mkdir", my_dir], capture_output=True)
    print(f"my_dir = {my_dir}")

    return (my_dict, my_dir)

# Returns true if the input string is of the format
# 3 numbers sepearated by ':'
def valid_sim(input_string):
    components = input_string.split(':')
    
    if len(components) != 3:
        return False
    
    try:
        for component in components:
            float(component)
    except ValueError:
        return False
    
    return True

# Returns the index of target in sim_list
# sim_list = list of simulations in a calibration experiment
# target   = workflow
def find_sim_index(sim_list, target):
    for i, sim in enumerate(sim_list):
        if sim["workflow"] == target:
            return i
    return -1

# Returns true if list1 is a proper subset of list2
def compare_lists_subset(list1, list2):
    counter1 = Counter(list1)
    counter2 = Counter(list2)
    
    return counter1.items() < counter2.items()

# Returns the index of target_list in exp_list
# exp_list    = list of experiments from JSON file
# target_list = list of workflow filenames
def find_exp_subset(exp_list, target_list):
    for i, exp in enumerate(exp_list):
        if compare_lists_subset(exp["calibrate"]["workflows"], target_list):
            return i
    return -1

# Returns true if elements in list1 are equal to list2 (allows elements to be in arbitrary order)
def compare_lists_unordered(list1, list2):
    counter1 = Counter(list1)
    counter2 = Counter(list2)
    
    return counter1 == counter2

# Returns the index of target_list in exp_list
# exp_list    = list of experiments from JSON file
# target_list = list of workflow filenames
def find_exp_index(exp_list, target_list):
    for i, exp in enumerate(exp_list):
        #if exp["calibrate"]["workflows"] == target_list:                           #lists need to be in the same order
        if compare_lists_unordered(exp["calibrate"]["workflows"], target_list):     #lists can be in arbitrary order
            return i
    return -1

# Returns the 'exp-*' directory from stdout
def find_exp_dir(stdout):
    if '~~~~~~~~~~~~~~~' in stdout:
        return stdout.split('~~~~~~~~~~~~~~~')[1].split('~~~~~~~~~~~~~~~')[0].strip()
    else:
        return 'ERROR'

# Returns True is the calibration completed
def valid_calibration(stdout):
    if '===============' in stdout:
        return True
    else:
        return False

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
                        help="output JSON file (only one)")

    parser.add_argument("-c", "--config_json", required=True,
                        action='append',
                        help="Config file (only one)")

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

    parser.add_argument('-d', '--use-docker', action='store_true',
                        help="Use Docker to run the simulator")

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
    config["use_docker"] = parsed_args.use_docker

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

# Calibrates on workflows in wf_list by running `calibrate.py`
# Returns a dictionary `cali_dict` with "workflows", "best_bo", and "best_rs" key/values inialized
    # wf_list       = list of workflow file names to calibrate
    # dir_wf        = directory containing workflows in wf_list
    # config_json   = config JSON file
    # num_iter      = maximum number of iterations
    # timeout       = maximum number of seconds per calibration (i.e., with --all, we expect roughly 2*timeout total seconds)
    # until_success = if true, will attempt to calibrate until success
    # max_attempts  = if until_sucess if false, the maximum number of attempts to calibrate
    # keep          = if true, does not delete the `exp-*` directory for the calibration
    # debug         = if true, prints debug statements
def calibrate(wf_list, dir_wf, config_json, num_iter, timeout, use_docker=True, until_success=True, max_attempts=20, keep=False, debug=True):
    cali_dict              = {}
    cali_dict["workflows"] = wf_list

    # Convert wf_list into a single string of workflows
    wf_string = ""
    for wf in wf_list:
        wf_string += str(os.path.abspath(dir_wf)) + '/' + str(wf) + ' '
    wf_string = wf_string.strip()

    # Command string
    cmd_string = str(os.path.abspath(calibrate_py)) + ' --config ' + str(os.path.abspath(config_json)) + ' --iter ' + str(num_iter) + ' --deephyper-timeout ' + str(timeout) + ' --all --workflows ' + wf_string
    if use_docker:
        cmd_string += " --docker "

    # Attempt to calibrate on workflows, until success or max_attempts
    full_timeout = 2*timeout + 20      # total time to consider a process as 'failed' (allow an overhead of 20s)
    attempt = 0
    while until_success or attempt <= max_attempts:
        try:
            calibrate_run = subprocess.run(cmd_string, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8", shell=True, timeout=full_timeout)
            
            # Rerun if errors are found
            # Otherwise returns a tuple containing (`best_bo.json`, `best_rs.json`) as dictionaries 
            exp_dir = find_exp_dir(calibrate_run.stdout)
            if "deephyper.core.exceptions.SearchTerminationError" in calibrate_run.stdout:
                if debug == True:
                    print(f"Attempt {attempt}: 'deephyper.core.exceptions.SearchTerminationError' detected... Retrying...")

                # Delete failed 'exp-*' directory
                subprocess.run(["rm", "-r", exp_dir]) 
            elif valid_calibration(calibrate_run.stdout) == "ERROR":
                if debug == True:
                    print(f"Attempt {attempt}: Error during calibration... Retrying...")
                    print(calibrate_run.stdout)

                # Delete failed 'exp-*' directory
                subprocess.run(["rm", "-r", exp_dir]) 
            else:
                if debug == True:
                    print(f"Attempt {attempt}: Success!")

                # Read 'best-bo.json'
                exp_bo = str(os.path.abspath(exp_dir)) + "/best-bo.json"
                if not os.path.isfile(exp_bo):
                    print(f"ERROR: {exp_bo} does not exist")
                    print(f"{calibrate_run.stdout}")
                    continue
                with open(exp_bo, "r") as fp:
                    cali_dict["best_bo"] = json.load(fp)

                # Read 'best-rs.json'
                exp_rs = str(os.path.abspath(exp_dir)) + "/best-rs.json"
                if not os.path.isfile(exp_rs):
                    print(f"ERROR: {exp_bs} does not exist")
                    print(f"{calibrate_run.stdout}")
                    continue
                with open(exp_rs, "r") as fp:
                    cali_dict["best_rs"] = json.load(fp)

                # If keep = False, delete 'exp-*' directory
                if keep == False:
                    subprocess.run(["rm", "-r", exp_dir]) 

                return cali_dict
        except subprocess.TimeoutExpired:
            if debug == True:
                print(f"Attempt {attempt}: Calibration took too long... Retrying...")

        attempt += 1

# Simulates workflows in wf_list using calibrations in `exp_dict`
# Does not re-simulate workflows that already exist in `exp_dict["simulate"]`
# Modifies `exp_dict["simulate"]` to contain new simulation results
# Assumes `exp_dict["calibrate"]` was initialized via calibrate(...)
# I.e., exp_dict["calibrate"]["best_bo"] and exp_dict["calibrate"]["best_rs"] contains the corresponding JSON
    # wf_list  = list of workflows to simulate
    # dir_wf   = directory containing workflows in wf_list
    # exp_dict = dictionary containing exp_dict["calibrate"]
    # my_dir   = directory to write `best_bo.json` and `best_rs.json` files
def simulate(wf_list, dir_wf, exp_dict, my_dir):
    if "calibrate" not in exp_dict:
        print(f"ERROR: Cannot perform simulation... exp_dict['calibrate'] does not exist!")
        return
    if not os.path.isdir(my_dir):
        proc = subprocess.run(["mkdir", my_dir], capture_output=True)
        if proc.returncode != 0:
            print(f"Failed to create directory '{my_dir}': {result.stderr.decode().strip()}")
            return

    # Create `best_bo.json` and `best_rs.json` files
    best_bo = str(os.path.abspath(my_dir)) + "/best_bo.json"
    best_rs = str(os.path.abspath(my_dir)) + "/best_rs.json"

    with open(best_bo, "w") as fp:
        fp.write(json.dumps(exp_dict["calibrate"]["best_bo"], indent=4))
    with open(best_rs, "w") as fp:
        fp.write(json.dumps(exp_dict["calibrate"]["best_rs"], indent=4))

    # Run simulations
    if "simulate" in exp_dict:
        # Simulate only new workflows in wf_list
        for wf in wf_list:
            sim_index = find_sim_index(exp_dict["simulate"], wf)

            if sim_index != -1:
                # Check if the existing simulation has errors
                if valid_sim(exp_dict["simulate"][sim_index]["bo"]) == False or valid_sim(exp_dict["simulate"][sim_index]["rs"]) == False:
                    print(f"Error in existing simulation for {wf}... Rerunning...")

                    sim_bo = subprocess.run([workflow_sim, best_bo, str(os.path.abspath(dir_wf)) + '/' + str(wf)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8")
                    exp_dict["simulate"][sim_index]["bo"] = sim_bo.stdout.strip()
                    print(f"Bayesian Optimization: {exp_dict['simulate'][sim_index]['bo']}")

                    sim_rs = subprocess.run([workflow_sim, best_rs, str(os.path.abspath(dir_wf)) + '/' + str(wf)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8")
                    exp_dict["simulate"][sim_index]["rs"] = sim_rs.stdout.strip()
                    print(f"Random Search        : {exp_dict['simulate'][sim_index]['rs']}")
            else:
                # New simulation
                exp_sim = {}
                exp_sim["workflow"] = wf
                print(f"Simulating {wf}")

                sim_bo = subprocess.run([workflow_sim, best_bo, str(os.path.abspath(dir_wf)) + '/' + str(wf)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8")
                exp_sim["bo"] = sim_bo.stdout.strip()
                print(f"Bayesian Optimization: {exp_sim['bo']}")

                sim_rs = subprocess.run([workflow_sim, best_rs, str(os.path.abspath(dir_wf)) + '/' + str(wf)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8")
                exp_sim["rs"] = sim_rs.stdout.strip()
                print(f"Random Search        : {exp_sim['rs']}")

                exp_dict["simulate"].append(exp_sim)
    else:
        exp_dict["simulate"] = list()

        # Simulate all workflows in wf_list
        for wf in wf_list:
            exp_sim = {}
            exp_sim["workflow"] = wf
            print(f"Simulating {wf}")

            sim_bo = subprocess.run([workflow_sim, best_bo, str(os.path.abspath(dir_wf)) + '/' + str(wf)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8")
            exp_sim["bo"] = sim_bo.stdout.strip()
            print(f"Bayesian Optimization: {exp_sim['bo']}")

            sim_rs = subprocess.run([workflow_sim, best_rs, str(os.path.abspath(dir_wf)) + '/' + str(wf)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8")
            exp_sim["rs"] = sim_rs.stdout.strip()
            print(f"Random Search        : {exp_sim['rs']}")

            exp_dict["simulate"].append(exp_sim)

    # Sort by workflow name
    exp_dict["simulate"] = sorted(exp_dict["simulate"], key=lambda x: x['workflow'])

# Calibrates on all workflows in cali_list
# Simulates on each workflow in sim_list
    # my_dict       = experiment dictionary
    # my_dir        = directory to write `best_bo.json` and `best_rs.json` files
    # cali_list     = list of workflow file names to calibrate
    # sim_list      = list of workflows to simulate
    # dir_wf        = directory containing workflows in wf_list
    # config_json   = config JSON file
    # num_iter      = maximum number of iterations
    # timeout       = maximum number of seconds per calibration (i.e., with --all, we expect roughly 2*timeout total seconds)
    # use_docker    = if true, use Docker
    # until_success = if true, will attempt to calibrate until success
    # max_attempts  = if until_sucess if false, the maximum number of attempts to calibrate
    # keep          = if true, does not delete the `exp-*` directory for the calibration
    # debug         = if true, prints debug statements
def calibrate_and_simulate(my_dict, my_dir, cali_list, sim_list, dir_wf, config_json, num_iter, timeout, use_docker=True, until_success=True, max_attempts=20, keep=False, debug=True):
    # Calibrate
    exp_index = find_exp_subset(my_dict["experiments"], cali_list)
    if exp_index != -1:
        # Previous calibration is missing calibration workflows
        # Remove from dictionary and redo calibration and simulation
        my_dict["experiments"].pop(exp_index)

    exp_index = find_exp_index(my_dict["experiments"], cali_list)
    exp_dict  = None
    if exp_index == -1:
        # New calibration
        exp_dict = {}

        print(f"\nCalibrating on = {cali_list}")
        exp_dict["calibrate"] = calibrate(cali_list, dir_wf, config_json, num_iter, timeout, use_docker=use_docker, until_success=until_success, max_attempts=max_attempts, keep=keep, debug=debug)
    else:
        # Calibration already exists
        print(f"\nSkipping calibration on = {cali_list}")
        exp_dict = my_dict["experiments"][exp_index]

    # Simulate
    simulate(sim_list, dir_wf, exp_dict, my_dir)

    # Save calibration and simulation results into my_dict
    if exp_index == -1:
        my_dict["experiments"].append(exp_dict)
    else:
        my_dict["experiments"][exp_index]["simulate"] = exp_dict["simulate"] #sorted(exp_dict["simulate"], key=lambda x: x['workflow'])
