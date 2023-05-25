#!/usr/bin/env python3

import os
import sys
import subprocess
import json
from argparse import ArgumentParser

import workflow_queries as wfq
import experiment_utils as exp_util

temp_best_bo = "temp_best_bo.json"
temp_best_rs = "temp_best_rs.json"

# Performs the 'vary tasks' experiment
# I.e., everything fixed, except # of tasks
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
        with open(outfile, "r+") as fp:
            my_dict = json.load(fp)
            # Check that JSON in outfile is consistent with this run
            # if my_dict["input_dir"] not == dir_wf:
            #     print(f"Workflow directories do not match!")
            #     sys.exit(1)
            if my_dict["config"] != config_json:
                print(f"Config files do not match!")
                sys.exit(1)
            # if my_dict["num_iter"] not == config_json:
            #     print(f"Number of iterations do not match!")
            #     sys.exit(1)
            if my_dict["timeout_seconds"] != timeout:
                print(f"Timeout does not match!")
                sys.exit(1)
    else:
        my_dict["input_dir"]           = dir_wf
        my_dict["config"]              = config_json
        my_dict["num_iter"]            = num_iter
        my_dict["timeout_seconds"]     = timeout
        my_dict["experiments"]         = list()

    if keep == False:
        keep_exp_dirs = exp_util.get_exp_list()

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
                                task_list = wfq.filter_tasks_eq(node_list, task)
                                wf_trials = wfq.get_trials(task_list)
                                wf_trials.sort()

                                # Calibrate on task_list
                                task_list.sort()

                                exp_index = exp_util.find_exp_subset(my_dict["experiments"], task_list)
                                if exp_index != -1:
                                    # Previous calibration is missing additional new trials
                                    # Remove from dictionary and redo calibration and simulation
                                    my_dict["experiments"].pop(exp_index)

                                exp_index = exp_util.find_exp_index(my_dict["experiments"], task_list)
                                if exp_index == -1:     
                                    # New calibration and simulation experiment
                                    exp_dict                           = {}
                                    exp_dict["calibrate"]              = {}
                                    exp_dict["calibrate"]["workflows"] = task_list

                                    print(f"\nCalibrating on = {task_list}")
                                    exp_hash = exp_util.calibrate(task_list, dir_wf, config_json, num_iter, timeout)

                                    # Read 'best-bo.json'
                                    exp_bo = str(os.path.abspath(exp_hash)) + "/best-bo.json"
                                    if not os.path.isfile(exp_bo):
                                        print(f"ERROR: {exp_bo} does not exist")
                                        continue
                                    else:
                                        fp = open(exp_bo)
                                        exp_dict["calibrate"]["best_bo"] = json.load(fp)
                                        fp.close()

                                    # Read 'best-rs.json'
                                    exp_rs = str(os.path.abspath(exp_hash)) + "/best-rs.json"
                                    if not os.path.isfile(exp_rs):
                                        print(f"ERROR: {exp_bs} does not exist")
                                        continue
                                    else:
                                        fp = open(exp_rs)
                                        exp_dict["calibrate"]["best_rs"] = json.load(fp)
                                        fp.close()

                                    # Simulate
                                    temp_sim_exp = list()
                                    sim_list = wfq.filter_nodes(
                                                wfq.filter_data_footprint( 
                                                 wfq.filter_cpu_frac(
                                                  wfq.filter_cpu_work(
                                                   wfq.filter_name(
                                                    wfq.filter_arch(simulate_list, arch), name), cpu_work), cpu_frac), data_footprint), node)
                                    for sim_wf in sim_list:
                                        exp_sim = {}
                                        exp_sim["workflow"] = sim_wf
                                        print(f"Simulating sim_wf = {sim_wf}")

                                        simulate_bo_stdout = exp_util.simluate(sim_wf, dir_wf, exp_bo)
                                        exp_sim["bo"] = simulate_bo_stdout.strip()
                                        print(f"Bayesian Optimization: {exp_sim['bo']}")

                                        simulate_rs_stdout = exp_util.simluate(sim_wf, dir_wf, exp_rs)
                                        exp_sim["rs"] = simulate_rs_stdout.strip()
                                        print(f"Random Search        : {exp_sim['rs']}")

                                        temp_sim_exp.append(exp_sim)

                                    exp_dict["simulate"] = sorted(temp_sim_exp, key=lambda x: x['workflow'])
                                    my_dict["experiments"].append(exp_dict)

                                    # If keep = False, delete newly created 'exp-*' directories
                                    if keep == False:
                                        exp_to_remove = exp_util.compare_lists(keep_exp_dirs, exp_util.get_exp_list())
                                        for exp_dir in exp_to_remove:
                                            subprocess.run(["rm", "-r", exp_dir])

                                    # Write for backup (just in case)
                                    with open(outfile, "w") as fp:
                                        fp.write(json.dumps(my_dict, indent=4))
                                else:
                                    # Calibration already exists, check for new simulations to perform
                                    print(f"\nSkipping calibration on = {task_list}")

                                    exp_dict = my_dict["experiments"][exp_index]

                                    with open(temp_best_bo, "w") as fp:
                                        fp.write(json.dumps(exp_dict["calibrate"]["best_bo"], indent=4))
                                    with open(temp_best_rs, "w") as fp:
                                        fp.write(json.dumps(exp_dict["calibrate"]["best_rs"], indent=4))

                                    sim_list = wfq.filter_nodes(
                                                wfq.filter_data_footprint( 
                                                 wfq.filter_cpu_frac(
                                                  wfq.filter_cpu_work(
                                                   wfq.filter_name(
                                                    wfq.filter_arch(simulate_list, arch), name), cpu_work), cpu_frac), data_footprint), node)
                                                             
                                    for sim_wf in sim_list:
                                        sim_index = exp_util.find_sim_index(exp_dict["simulate"], sim_wf)

                                        if sim_index != -1:
                                            # Check if the existing simulation has errors
                                            if exp_util.valid_sim(exp_dict["simulate"][sim_index]["bo"]) == False or exp_util.valid_sim(exp_dict["simulate"][sim_index]["rs"]) == False:
                                                print(f"Error in existing simulation for sim_wf = {sim_wf}... Rerunning simulations...")

                                                simulate_bo_stdout = exp_util.simluate(sim_wf, dir_wf, temp_best_bo)
                                                exp_dict["simulate"][sim_index]["bo"] = simulate_bo_stdout.strip()
                                                print(f"Bayesian Optimization: {exp_dict['simulate'][sim_index]['bo']}")

                                                simulate_rs_stdout = exp_util.simluate(sim_wf, dir_wf, temp_best_rs)
                                                exp_dict["simulate"][sim_index]["rs"] = simulate_rs_stdout.strip()
                                                print(f"Random Search        : {exp_dict['simulate'][sim_index]['rs']}")                                      
                                        else:
                                            # New simulation
                                            exp_sim = {}
                                            exp_sim["workflow"] = sim_wf
                                            print(f"Simulating sim_wf = {sim_wf}")

                                            simulate_bo_stdout = exp_util.simluate(sim_wf, dir_wf, temp_best_bo)
                                            exp_sim["bo"] = simulate_bo_stdout.strip()
                                            print(f"Bayesian Optimization: {exp_sim['bo']}")

                                            simulate_rs_stdout = exp_util.simluate(sim_wf, dir_wf, temp_best_rs)
                                            exp_sim["rs"] = simulate_rs_stdout.strip()
                                            print(f"Random Search        : {exp_sim['rs']}")

                                            exp_dict["simulate"].append(exp_sim)

                                    my_dict["experiments"][exp_index]["simluate"] = sorted(exp_dict["simulate"], key=lambda x: x['workflow'])

                                    # Write for backup (just in case)
                                    with open(outfile, "w") as fp:
                                        fp.write(json.dumps(my_dict, indent=4))

    # Write finished my_dict
    with open(outfile, "w") as fp:
        fp.write(json.dumps(my_dict, indent=4))

def main():
    # Parse arguments
    config = exp_util.parse_arguments(sys.argv)

    calibrate_list = exp_util.parse_calibrate_args(config, debug=False)
    simulate_list  = exp_util.parse_simulate_args(config, debug=False)

    # Run vary_tasks experiment
    vary_tasks(calibrate_list, simulate_list, config['input_dir'], config['config_json'], config["output_file"], config['num_iter'], config['timeout'], config['keep_exp_dir'])

if __name__ == "__main__":
    main()