#!/usr/bin/env python3

import os
import sys
import json
import argparse
import matplotlib.pyplot as plt
from argparse import ArgumentParser

import workflow_queries as wfq

def scatter_plot(data, filename):
    x = list(range(len(data)))  # Use index as x-axis values
    y1 = [point[0] for point in data]  # First series
    y2 = [point[1] for point in data]  # Second series
    
    plt.scatter(x, y2, marker='o', s=5, label='Bayesian Optimization')
    plt.scatter(x, y1, marker='x', s=5, label='Random Search')
    
    plt.xlabel('Workflows')
    plt.ylabel('Error')

    plt.legend()  # Show legend
    plt.savefig(filename, format='pdf')  # Save plot as PDF
    plt.close()  # Close the figure to release memory

def line_plot(data, filename):
    x = list(range(len(data)))  # Use index as x-axis values
    y1 = [point[0] for point in data]  # First series
    y2 = [point[1] for point in data]  # Second series
    
    plt.plot(x, y1, label='Random Search')
    plt.plot(x, y2, label='Bayesian Optimization')
    plt.xlabel('Workflows')
    plt.ylabel('Error')

    plt.legend()  # Show legend
    plt.savefig(filename, format='pdf')  # Save plot as PDF
    plt.close()  # Close the figure to release memory

def count_tuples(data):
    count = 0
    for point in data:
        if point[0] < point[1]:
            count += 1
    return count

def get_json_filename():
    parser = argparse.ArgumentParser()

    parser.add_argument("-i", "--input", required=True,
                        action='append',
                        help="Input directory containing workflow JSON files (only one)")

    # Parse the command-line arguments
    args = parser.parse_args()
    print(f"{args.input}")

    # Input workflow dir
    input_values = args.input
    if len(input_values) > 1:
        sys.stderr.write("Error: a single -i/--input argument should be specified\n")
        sys.exit(1)
    if not os.path.exists(input_values[0]):
        sys.stderr.write("Error: input file '" + input_values[0] + "' does not exist\n")
        sys.exit(1)
    return input_values[0]

def main():
    filename = get_json_filename()

    fp = open(filename)
    run_dict = json.load(fp)
    fp.close()

    filename = filename.split('.json')[0]
    # print(f"{filename}")

    data      = list()
    sim_list  = list()
    count_err = 0
    iter_rs   = 0
    iter_bo   = 0
    for exp in run_dict["experiments"]:
        iter_rs += int(exp['calibrate']['best_rs']['calibration']['nb_iter'])
        iter_bo += int(exp['calibrate']['best_bo']['calibration']['nb_iter'])

        for sim in exp["simulate"]:
            sim_list.append(sim)
            try:
                rs = float(sim["rs"].split(":")[2]) #* 100.
                bo = float(sim["bo"].split(":")[2]) #* 100.
                data.append((rs, bo))
            except ValueError:
                count_err += 1
    data.sort()
    if count_err == 0:
        print("All simulations completed")
    else:
        print(f"{count_err} simulations did not complete")
    iter_rs /= len(run_dict["experiments"])
    iter_bo /= len(run_dict["experiments"])
    print(f"Average # of iterations (Random Search)         = {iter_rs}")
    print(f"Average # of iterations (Bayesian Optimization) = {iter_bo}")
    print(f"Random beats Bayesian ==> {count_tuples(data)} / {len(data)} = {float(count_tuples(data)/len(data))}")
    scatter_plot(data, filename + '.pdf')


    print("\nFiltering by workflow:")
    wf_names = ["genome", "montage", "seismology", "chain", "forkjoin"]
    for name in wf_names:
        data      = list()
        count_err = 0
        for sim in sim_list:
            if wfq.name_equal(sim["workflow"], name):
                try:
                    rs = float(sim["rs"].split(":")[2]) #* 100.
                    bo = float(sim["bo"].split(":")[2]) #* 100.
                    data.append((rs, bo))
                except:
                    count_err += 1
        data.sort()
        print(f"Random beats Bayesian ({name} only) ==> {count_tuples(data)} / {len(data)} = {float(count_tuples(data)/len(data))}")
        # scatter_plot(data, filename + '_' + name + '.pdf')

    print("\nFiltering by cpu work:")
    cpu_work = [0, 500, 1000, 2000, 5000]
    for work in cpu_work:
        data      = list()
        count_err = 0
        for sim in sim_list:
            if wfq.cpu_work_equal(sim["workflow"], work):
                try:
                    rs = float(sim["rs"].split(":")[2]) #* 100.
                    bo = float(sim["bo"].split(":")[2]) #* 100.
                    data.append((rs, bo))
                except:
                    count_err += 1
        data.sort()
        print(f"Random beats Bayesian (cpu_work = {work} only) ==> {count_tuples(data)} / {len(data)} = {float(count_tuples(data)/len(data))}")
        # scatter_plot(data, filename + '_cpu_work_' + str(work) + '.pdf')

    print("\nFiltering by data footprint:")
    data_fp = [0, 100000000, 1000000000, 10000000000]
    for dfp in data_fp:
        data      = list()
        count_err = 0
        for sim in sim_list:
            if wfq.data_footprint_equal(sim["workflow"], dfp):
                try:
                    rs = float(sim["rs"].split(":")[2]) #* 100.
                    bo = float(sim["bo"].split(":")[2]) #* 100.
                    data.append((rs, bo))
                except:
                    count_err += 1
        data.sort()
        print(f"Random beats Bayesian (data footprint = {dfp} only) ==> {count_tuples(data)} / {len(data)} = {float(count_tuples(data)/len(data))}")
        # scatter_plot(data, filename + '_data_footprint_' + str(dfp) + '.pdf')

if __name__ == "__main__":
    main()
