#!/usr/bin/env python3

import os
import sys
import subprocess
import json
from argparse import ArgumentParser

import workflow_queries as wfq
import experiment_utils as exp_util

# Performs the '' experiment
# Calibrate on fixed architecture, workflow, number of nodes, and number of tasks
# Simulate  on fixed architecture, workflow, and number of nodes
    # calibrate_list = list of workflows to calibrate
    # simulate_lsit  = list of workflows to simulate
    # config_json    = config JSON file
    # dir_wf         = directory containing workflows in calibrate_list and simulate_list
    # outfile        = output JSON file name (without the .json extension)
    # num_iter       = maximum number of iterations used in calibrate.py (--iter)
    # timeout        = maximum number of seconds used in calibrate.py (--deephyper-timeout)
    # keep           = if true, does not delete exp-* directories
    # debug          = if true, prints debug statements
def vary_tasks_fix_arch_wf_nodes(calibrate_list, simulate_list, dir_wf, config_json, outfile, num_iter=500, timeout=60, keep=False, debug=False):
    my_dict, my_dir = exp_util.init_experiment(dir_wf, config_json, outfile, num_iter, timeout)

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
            wf_nodes    = wfq.get_nodes(name_list)
            wf_nodes.sort()

            for node in wf_nodes:  #for each node
                if debug == True:
                    print(f"    nodes = {node}")
                node_list = wfq.filter_node(name_list, node)
                wf_tasks  = wfq.get_tasks(node_list)
                wf_tasks.sort()

                for task in wf_tasks:  #for each task
                    if debug == True:
                        print(f"      task = {task}")

                    # Calibrate on task_list
                    task_list = wfq.filter_tasks_eq(node_list, task)
                    task_list.sort()

                    # Simulate on fixed architecture, workflow, and number of nodes
                    temp_sim_exp = list()
                    sim_list = wfq.filter_nodes(
                                wfq.filter_name(
                                 wfq.filter_arch(simulate_list, arch), name), node)
                    sim_list.sort()

                    exp_util.calibrate_and_simulate(my_dict, my_dir, task_list, sim_list, dir_wf, config_json, num_iter, timeout, keep=keep)

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

    # Run vary_tasks_fix_arch_wf_nodes experiment
    vary_tasks_fix_arch_wf_nodes(calibrate_list, simulate_list, config['input_dir'], config['config_json'], config["output_file"], config['num_iter'], config['timeout'], config['keep_exp_dir'])

if __name__ == "__main__":
    main()