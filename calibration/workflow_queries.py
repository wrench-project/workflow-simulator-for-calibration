#!/usr/bin/env python3

import os
import sys

#0 <workflow name>-
#1 <number of tasks>-
#2 <cpu work>-
#3 <cpu fraction>-
#4 <data footprint in bytes>-
#5 <architecture>-
#6 <number of compute nodes>-
#7 <trial number>-
#8 <timestamp>[.tar.gz|.json]
# For instance: cycles-69-0-0.6-0-haswell-1-0-1682541788.json

###############################################################################

#Returns a list of workflow names in wf_list
def get_names(wf_list):
    my_set = set()
    for wf in wf_list:
        my_set.add(wf.split('-')[0])
    return list(my_set)

def name_equal(wf, name):
    return wf.split('-')[0] == name

#Returns a list of workflows from wf_list, such that
#name == wf_name
def filter_name(wf_list, wf_name):
    my_list = list()
    for wf in wf_list:
        if wf.split('-')[0] == wf_name:
            my_list.append(wf)
    return my_list

#Returns a list of workflows from wf_list, such that
#name in wf_names
def filter_names(wf_list, wf_names):
    my_list = list()
    for wf in wf_list:
        if wf.split('-')[0] in wf_names:
            my_list.append(wf)
    return my_list

###############################################################################

#Returns a list of tasks in wf_list
def get_tasks(wf_list):
    my_set = set()
    for wf in wf_list:
        my_set.add(wf.split('-')[1])
    return list(my_set)

def tasks_equal(wf, num_tasks):
    return int(wf.split('-')[1]) == int(num_tasks)

def tasks_leq(wf, num_tasks):
    return int(wf.split('-')[1]) <= int(num_tasks)

def tasks_geq(wf, num_tasks):
    return int(wf.split('-')[1]) >= int(num_tasks)

#Returns a list of workflows from wf_list, such that
#tasks == num_tasks
def filter_tasks_eq(wf_list, num_tasks):
    my_list = list()
    for wf in wf_list:
        if tasks_equal(wf, num_tasks):
            my_list.append(wf)
    return my_list

#Returns a list of workflows from wf_list, such that
#tasks == num_tasks
def filter_tasks(wf_list, num_tasks):
    my_list = list()
    for wf in wf_list:
        for task in num_tasks:
            if tasks_equal(wf, task):
                my_list.append(wf)
    return my_list

#Returns a list of workflows from wf_list, such that
#num_tasks_min <= tasks <= num_tasks_max
def filter_tasks_range(wf_list, num_tasks_min, num_tasks_max):
    my_list = list()
    for wf in wf_list:
        if tasks_geq(wf, num_tasks_min) and tasks_leq(wf, num_tasks_max):
            my_list.append(wf)
    return my_list



###############################################################################

#Returns a list of cpu_work in wf_list
def get_cpu_work(wf_list):
    my_set = set()
    for wf in wf_list:
        my_set.add(wf.split('-')[2])
    return list(my_set)

def cpu_work_equal(wf, num_cpu_work):
    return int(wf.split('-')[2]) == int(num_cpu_work)

#Returns a list of workflows from wf_list, such that
#cpu_work == num_cpu_work
def filter_cpu_work(wf_list, num_cpu_work):
    my_list = list()
    for wf in wf_list:
        if cpu_work_equal(wf, num_cpu_work):
            my_list.append(wf)
    return my_list

#Returns a list of workflows from wf_list, such that
#cpu_work == num_cpu_works
def filter_cpu_works(wf_list, num_cpu_works):
    my_list = list()
    for wf in wf_list:
        for work in num_cpu_works:
            if cpu_work_equal(wf, work):
                my_list.append(wf)
    return my_list

###############################################################################

#Returns a list of cpu_frac in wf_list
def get_cpu_frac(wf_list):
    my_set = set()
    for wf in wf_list:
        my_set.add(wf.split('-')[3])
    return list(my_set)

def cpu_frac_equal(wf, num_cpu_frac):
    return float(wf.split('-')[3]) == float(num_cpu_frac)

#Returns a list of workflows from wf_list, such that
#cpu_fraq == num_cpu_frac
def filter_cpu_frac(wf_list, num_cpu_frac):
    my_list = list()
    for wf in wf_list:
        if cpu_frac_equal(wf, num_cpu_frac):
            my_list.append(wf)
    return my_list

#Returns a list of workflows from wf_list, such that
#cpu_fraq == num_cpu_fracs
def filter_cpu_fracs(wf_list, num_cpu_fracs):
    my_list = list()
    for wf in wf_list:
        for frac in num_cpu_fracs:
            if cpu_frac_equal(wf, frac):
                my_list.append(wf)
    return my_list

###############################################################################

#Returns a list of data footprint in wf_list
def get_data_footprint(wf_list):
    my_set = set()
    for wf in wf_list:
        my_set.add(wf.split('-')[4])
    return list(my_set)

def data_footprint_equal(wf, num_data_footprint):
    return int(wf.split('-')[4]) == int(num_data_footprint)

#Returns a list of workflows from wf_list, such that
#data_footprint == num_data_footprint
def filter_data_footprint(wf_list, num_data_footprint):
    my_list = list()
    for wf in wf_list:
        if data_footprint_equal(wf, num_data_footprint):
            my_list.append(wf)
    return my_list

#Returns a list of workflows from wf_list, such that
#data_footprint == num_data_footprints
def filter_data_footprints(wf_list, num_data_footprints):
    my_list = list()
    for wf in wf_list:
        for data_fp in num_data_footprints:
            if data_footprint_equal(wf, data_fp):
                my_list.append(wf)
    return my_list

###############################################################################

#Returns a list of architectures in wf_list
def get_arch(wf_list):
    my_set = set()
    for wf in wf_list:
        my_set.add(wf.split('-')[5])
    return list(my_set)

#Returns a list of workflows from wf_list, such that
#arch == wf_arch
def filter_arch(wf_list, wf_arch):
    my_list = list()
    for wf in wf_list:
        if wf.split('-')[5] == wf_arch:
            my_list.append(wf)
    return my_list

#Returns a list of workflows from wf_list, such that
#arch in wf_archs
def filter_archs(wf_list, wf_archs):
    my_list = list()
    for wf in wf_list:
        if wf.split('-')[5] in wf_archs:
            my_list.append(wf)
    return my_list

###############################################################################

#Returns a list of number of nodes in wf_list
def get_nodes(wf_list):
    my_set = set()
    for wf in wf_list:
        my_set.add(wf.split('-')[6])
    return list(my_set)

def node_equal(wf, num_node):
    return int(wf.split('-')[6]) == int(num_node)

#Returns a list of workflows from wf_list, such that
#nodes == num_nodes
def filter_node(wf_list, num_node):
    my_list = list()
    for wf in wf_list:
        if node_equal(wf, num_node):
            my_list.append(wf)
    return my_list

#Returns a list of workflows from wf_list, such that
#node in num_nodes
def filter_nodes(wf_list, num_nodes):
    my_list = list()
    for wf in wf_list:
        for node in num_nodes:
            if node_equal(wf, node):
                my_list.append(wf)
    return my_list

###############################################################################

#Returns a list of trial numbers in wf_list
def get_trials(wf_list):
    my_set = set()
    for wf in wf_list:
        my_set.add(wf.split('-')[7])
    return list(my_set)

###############################################################################

#Returns a list of all workflow JSON files in dir
def get_workflows(dir):
    if not os.path.isdir(dir):
        print(f"{dir} is not a directory")
        return
    return os.listdir(dir)

###############################################################################

def main():
    #1. Command line arguments
    argc = len(sys.argv)
    if (argc != 2):
        print(f"Usage: python3 {sys.argv[0]} <directory of json workflows>")
        quit()

    wf_list = get_workflows(sys.argv[1])
    #print(f"{wf_list}")

    wf_names    = get_names(wf_list)
    wf_tasks    = get_tasks(wf_list)
    wf_cpu_work = get_cpu_work(wf_list)
    wf_cpu_frac = get_cpu_frac(wf_list)
    wf_data_fp  = get_data_footprint(wf_list)
    wf_arch     = get_arch(wf_list)
    wf_nodes    = get_nodes(wf_list)
    wf_trials   = get_trials(wf_list)

    print(f"names = {wf_names}")
    print(f"tasks = {wf_tasks}")
    print(f"cpu_work = {wf_cpu_work}")
    print(f"cpu_frac = {wf_cpu_frac}")
    print(f"wf_data_fp = {wf_data_fp}")
    print(f"wf_arch = {wf_arch}")
    print(f"wf_nodes = {wf_nodes}")
    print(f"wf_trials = {wf_trials}")

if __name__ == "__main__":
    main()
