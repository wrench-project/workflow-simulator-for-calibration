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
			file_token=file_path.split("/")[-1].split("-")
			try:
				print("mv","\""+file_path+"\"",f"\"{"\\".join(file_path.split("/")[0:-1])}-one_workflow-{tokens[0]}-{max(data.experiments[0].training_set_spec.num_nodes_values)}-{max(data.experiments[0].training_set_spec.num_tasks_values)}-{file_token[-6]}.pickled\"")
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


def process_experiment_group(experiment_group: [ExperimentSet]):
	name=[experiment_group[0][0].training_set_spec.workflows[0][0].split("/")[-1].split("-")[0],#actual workflow name
		  #experiment_group[0].get_architecture(),
		  #experiment_group[0].simulator.compute_service_scheme,
		  #experiment_group[0].simulator.storage_service_scheme,
		  #experiment_group[0].simulator.network_topology_scheme,
		  experiment_group[0].algorithm,
		  #experiment_group[0].loss_function,
		  #experiment_group[0].time_limit,
		  #experiment_group[0].num_threads
		  ]
	#print(name)
	name = [str(x) for x in name]
	#print(name)
	network = set()
	storage = set()
	compute = set()

	#print(name)
	# sys.stderr.write("Processing ")
	figure_name = f"figure-sophistication_experiments-"+\
				"-".join(name)+".pdf"
				  

	

	to_plot = defaultdict(lambda: defaultdict(dict))
	largest_value = 0
	for experiment_set in experiment_group:
		for result in experiment_set.experiments:
			training_loss = result.calibration_loss
			result.training_set_spec.update_fields()
			training_spec = result.training_set_spec
			#print(vars(experiment_set.simulator))
			#print(result.training_set_spec.num_nodes_values)
			#print(result.training_set_spec.num_tasks_values)
			network.add(experiment_set.simulator.compute_service_scheme)
			storage.add(experiment_set.simulator.storage_service_scheme)
			compute.add(experiment_set.simulator.network_topology_scheme)
			
			to_plot[experiment_set.simulator.compute_service_scheme]\
			       [experiment_set.simulator.storage_service_scheme]\
			       [experiment_set.simulator.network_topology_scheme]\
				   =({"training_loss":training_loss,
				      "evaluation_losses": result.evaluation_losses[0]})
			#task_counts.add(max(result.training_set_spec.num_tasks_values))
			#node_counts.add(max(result.training_set_spec.num_nodes_values))
	#to_plot = dict(sorted(to_plot.items()))
	for key in to_plot.keys():
		to_plot[key]=dict(to_plot[key])
	data=dict(to_plot)


	categories = []
	training_losses = []
	evaluation_losses = []

	for system, modes in data.items():
		for mode, links in modes.items():
			for link, metrics in links.items():
				categories.append(f"{system} | {mode} | {link}")
				training_losses.append(metrics['training_loss'])
				evaluation_losses.append(metrics['evaluation_losses'])

	# Plot
	fig, axs = plt.subplots(2, 1, figsize=(10, 12), sharex=True)

	# Training Loss
	axs[0].barh(categories, training_losses, color='skyblue', edgecolor='black')
	axs[0].set_title('Training Loss')
	axs[0].set_xlabel('Loss')
	axs[0].set_ylabel('Configuration')
	axs[0].invert_yaxis()

	# Evaluation Loss
	axs[1].barh(categories, evaluation_losses, color='lightgreen', edgecolor='black')
	axs[1].set_title('Evaluation Loss')
	axs[1].set_xlabel('Loss')
	axs[1].set_ylabel('Configuration')
	axs[1].invert_yaxis()

	plt.tight_layout()
	plt.show()
	fig.colorbar(cm.ScalarMappable(norm=norm, cmap=cmap), ax=ax, orientation='vertical', fraction=0.02, pad=0.04)
	plt.suptitle(" ".join(name))
	sys.stderr.write(f"Saving {figure_name}...\n")
	plt.savefig(figure_name, bbox_inches='tight')
	plt.close()


def main():
	pickle_files = []
	for arg in sys.argv[1:]:
		if '*' in arg:
			pickle_files+=glob(arg)
		else:
			pickle_files.append(arg)
	data=load_and_group_pickles(pickle_files)
	sys.stderr.write(f"Found {len(pickle_files)} pickled files to process...\n")
	for group in data.values():
		process_experiment_group(group)


if __name__ == "__main__":
	main()
