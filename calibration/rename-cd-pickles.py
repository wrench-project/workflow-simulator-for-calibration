#!/usr/bin/env python3
import argparse
import sys
from glob import glob
import pickle 
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import gridspec
from matplotlib.colors import Normalize
from matplotlib import cm
from Util import *
from collections import defaultdict

def load_and_group_pickles(file_paths):

	grouped_data = defaultdict(list)
	
	for file_path in file_paths:
		with open(file_path, 'rb') as file:
			data = pickle.load(file)
			tokens=data.experiments[0].training_set_spec.workflows[0][0].split("/")[-1].split("-")
			key = tokens[0]+data.algorithm
			grouped_data[key].append(data)
			data.experiments[0].training_set_spec.update_fields()
			file_path=file_path.replace("\\","/")
			file_token=file_path.split("/")[-1].split("-")
			#print(tokens)
			#0-workflow
			#1-tasks
			#2-CPU 
			#3-Fixed (1.0 (sometimes))
			#4-data
			#5-architecture
			#6-Num nodes
			#7-trial number (inc)
			#8-timestamp
			try:
				print("mv","\""+file_path+"\"",f"\"{"/".join(file_path.split("/")[0:-1])}/cpu_data-{tokens[0]}-{tokens[2]}-{tokens[4]}-{file_token[-6]}-{file_token[-2]}.pickled\"")
				#print(f"\"{"/".join(file_path.split("/")[0:-1])}/cpu_data-{tokens[0]}-{tokens[2]}-{tokens[4]}-{file_token[-6]}-{file_token[-2]}.pickled\"")
			except:
				pass
	return dict(grouped_data)

def build_label(workflow_sec_spec: WorkflowSetSpec):
	label = ""
	label += (",".join([str(x) for x in workflow_sec_spec.num_tasks_values])) + "-"
	label += (",".join([str(x) for x in workflow_sec_spec.num_nodes_values])) + "-"
	if len(workflow_sec_spec.cpu_values) > 1:
		label += "ALL-"
	else:
		label += "ONE-"
	if len(workflow_sec_spec.data_values) > 1:
		label += "ALL"
	else:
		label += "ONE"
	return label




def main():
	pickle_files = []
	for arg in sys.argv[1:]:
		if '*' in arg:
			pickle_files+=glob(arg)
		else:
			pickle_files.append(arg)
	data=load_and_group_pickles(pickle_files)
	
if __name__ == "__main__":
	main()
