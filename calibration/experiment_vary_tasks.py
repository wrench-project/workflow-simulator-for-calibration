#!/usr/bin/env python3

import os
import sys
import subprocess
import json
from argparse import ArgumentParser

import workflow_queries as wfq
import experiment_utils as exp_util

# Performs the 'vary tasks' experiment
# Calibrate on everything fixed, except # of trials
# Simulate  on everything fixed, except # of tasks and trials
    # calibrate_list = list of workflows to calibrate
    # simulate_lsit  = list of workflows to simulate
    # config_json    = config JSON file
    # dir_wf         = directory containing workflows in calibrate_list and simulate_list
    # outfile        = output JSON file name (without the .json extension)
    # num_iter       = maximum number of iterations used in calibrate.py (--iter)
    # timeout        = maximum number of seconds used in calibrate.py (--deephyper-timeout)
    # keep           = if true, does not delete exp-* directories
    # debug          = if true, prints debug statements
def vary_tasks(calibrate_list, simulate_list, dir_wf, config_json, outfile, num_iter=500, timeout=60, keep=False, debug=False):
    my_dict = {}

    if os.path.exists(outfile):
        with open(outfile, "r") as fp:
            my_dict = json.load(fp)

            if my_dict["config"] != config_json:
                print(f"Config files do not match!")
                sys.exit(1)
            if my_dict["timeout_seconds"] != timeout:
                print(f"Timeout does not match!")
                sys.exit(1)
    else:
        my_dict["input_dir"]           = dir_wf
        my_dict["config"]              = config_json
        my_dict["num_iter"]            = num_iter
        my_dict["timeout_seconds"]     = timeout
        my_dict["experiments"]         = list()

    # Generate unique directory name
    my_dir = "run-" + exp_util.generate_random_string()
    while os.path.isdir(my_dir):
        my_dir = "run-" + exp_util.generate_random_string()

    # Create directory
    mkdir_proc = subprocess.run(["mkdir", my_dir], capture_output=True)
    while mkdir_proc.returncode != 0:
        mkdir_proc = subprocess.run(["mkdir", my_dir], capture_output=True)
    print(f"my_dir = {my_dir}")

    wf_arch = wfq.get_arch(calibrate_list)
    wf_arch.sort()
    if debug == True:
        print(wf_arch)

    for arch in wf_arch:    #for each architecture
        if debug == True:
            print(f"\narch = {arch}")
        arch_list = wfq.filter_arch(calibrate_list, arch)
        wf_names  = wfq.get_names(arch_list)
        wf_names.sort()

        for name in wf_names:   #for each workflow
            if debug == True:
                print(f"  workflow name = {name}")
            name_list   = wfq.filter_name(arch_list, name)
            wf_cpu_work = wfq.get_cpu_work(name_list)
            wf_cpu_work.sort()

            for cpu_work in wf_cpu_work:    #for each cpu_work
                if debug == True:
                    print(f"    cpu_work = {cpu_work}")
                cpu_work_list = wfq.filter_cpu_work(name_list, cpu_work)
                wf_cpu_frac   = wfq.get_cpu_frac(cpu_work_list)
                wf_cpu_frac.sort()

                for cpu_frac in wf_cpu_frac:    #for each cpu_frac
                    if debug == True:
                        print(f"      cpu_frac = {cpu_frac}")
                    cpu_frac_list     = wfq.filter_cpu_frac(cpu_work_list, cpu_frac)
                    wf_data_footprint = wfq.get_data_footprint(cpu_frac_list)
                    wf_data_footprint.sort()

                    for data_footprint in wf_data_footprint:    #for each data_footprint
                        if debug == True:
                            print(f"        data_footprint = {data_footprint}")
                        data_footprint_list = wfq.filter_data_footprint(cpu_frac_list, data_footprint)
                        wf_nodes            = wfq.get_nodes(data_footprint_list)
                        wf_nodes.sort()

                        for node in wf_nodes:  #for each nodes
                            if debug == True:
                                print(f"          nodes = {node}")
                            node_list = wfq.filter_node(data_footprint_list, node)
                            wf_tasks  = wfq.get_tasks(node_list)
                            wf_tasks.sort()

                            for task in wf_tasks:  #for each task
                                if debug == True:
                                    print(f"            task = {task}")

                                # Calibrate on task_list
                                task_list = wfq.filter_tasks_eq(node_list, task)
                                task_list.sort()

                                exp_index = exp_util.find_exp_subset(my_dict["experiments"], task_list)
                                if exp_index != -1:
                                    # Previous calibration is missing calibration workflows
                                    # Remove from dictionary and redo calibration and simulation
                                    my_dict["experiments"].pop(exp_index)

                                exp_index = exp_util.find_exp_index(my_dict["experiments"], task_list)
                                exp_dict  = None
                                if exp_index == -1:
                                    # New calibration
                                    exp_dict = {}

                                    print(f"\nCalibrating on = {task_list}")
                                    exp_dict["calibrate"] = exp_util.calibrate(task_list, dir_wf, config_json, num_iter, timeout, keep=keep)
                                else:
                                    # Calibration already exists
                                    print(f"\nSkipping calibration on = {task_list}")
                                    exp_dict = my_dict["experiments"][exp_index]

                                # Simulate on everything fixed, except tasks and trials
                                temp_sim_exp = list()
                                sim_list = wfq.filter_nodes(
                                            wfq.filter_data_footprint( 
                                             wfq.filter_cpu_frac(
                                              wfq.filter_cpu_work(
                                               wfq.filter_name(
                                                wfq.filter_arch(simulate_list, arch), name), cpu_work), cpu_frac), data_footprint), node)
                                sim_list.sort()
                                exp_util.simulate(sim_list, dir_wf, exp_dict, my_dir)

                                # Save calibration and simulation results into my_dict
                                if exp_index == -1:
                                    my_dict["experiments"].append(exp_dict)
                                else:
                                    my_dict["experiments"][exp_index]["simulate"] = exp_dict["simulate"] #sorted(exp_dict["simulate"], key=lambda x: x['workflow'])

                                # Write for backup (just in case)
                                with open(outfile, "w") as fp:
                                    fp.write(json.dumps(my_dict, indent=4))
                                    
    # Write finished my_dict
    with open(outfile, "w") as fp:
        fp.write(json.dumps(my_dict, indent=4))

    # Remove my_dir
    subprocess.run(["rm", "-r", my_dir])

def main():
    # Parse arguments
    config = exp_util.parse_arguments(sys.argv)

    calibrate_list = exp_util.parse_calibrate_args(config, debug=False)
    simulate_list  = exp_util.parse_simulate_args(config, debug=False)

    # Run vary_tasks experiment
    vary_tasks(calibrate_list, simulate_list, config['input_dir'], config['config_json'], config["output_file"], config['num_iter'], config['timeout'], config['keep_exp_dir'])

if __name__ == "__main__":
    main()