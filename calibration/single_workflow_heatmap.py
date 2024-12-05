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
			print("mv",file_path,f"{file_token[0]}-one_workflow-{tokens[0]}-{max(data.experiments[0].training_set_spec.num_nodes_values)}-{max(data.experiments[0].training_set_spec.num_tasks_values)}-{file_token[7]}.pickled")
	
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
	name = [str(x) for x in name]
	task_counts = set()
	node_counts = set()

	#print(name)
	# sys.stderr.write("Processing ")
	figure_name = f"figure-one_workflow_experiments-"+\
				"-".join(name)+".pdf"
				  

	

	to_plot = defaultdict(dict)
	largest_value = 0
	for experiment_set in experiment_group:
		for result in experiment_set.experiments:
			training_loss = result.calibration_loss
			result.training_set_spec.update_fields()
			training_spec = result.training_set_spec
			#print(experiment_set)
			#print(result.training_set_spec.num_nodes_values)
			#print(result.training_set_spec.num_tasks_values)
			
			to_plot[max(result.training_set_spec.num_nodes_values)]\
			       [max(result.training_set_spec.num_tasks_values)]\
				   =({"training_loss":training_loss,
				      "evaluation_losses": result.evaluation_losses})
			task_counts.add(max(result.training_set_spec.num_tasks_values))
			node_counts.add(max(result.training_set_spec.num_nodes_values))
	#to_plot = dict(sorted(to_plot.items()))
	data=to_plot
	#data = {
	#	1: {//node
	#		1: //task
	#          {'training_loss': 0.1, 'evaluation_losses': [0.2, 0.3, 0.25]},
	#		2: {'training_loss': 0.15, 'evaluation_losses': [0.1, 0.2, 0.15]},
	#	},
	#	2: {
	#		1: {'training_loss': 0.2, 'evaluation_losses': [0.3, 0.4, 0.35]},
	#		2: {'training_loss': 0.25, 'evaluation_losses': [0.2, 0.3, 0.25]},
	#	},
	##}

	# Extract task and node counts
	task_counts = sorted(list(task_counts),reverse=True)
	node_counts = sorted(list(node_counts))
	#print(task_counts)
	#print(node_counts)
	# Initialize arrays for the heatmaps
	single_loss_array = np.full((len(task_counts), len(node_counts)), np.nan)
	average_loss_array = np.full((len(task_counts), len(node_counts)), np.nan)
	max_loss_array = np.full((len(task_counts), len(node_counts)), np.nan)
	
	# Populate arrays with data
	for i, task in enumerate(task_counts):
		for j, node in enumerate(node_counts):

			if task in data[node]:
				entry = data[node][task]
				single_loss_array[i, j] = round(entry['training_loss'],3)
				average_loss_array[i, j] = round(np.mean(entry['evaluation_losses']),3)
				max_loss_array[i, j] = round(np.max(entry['evaluation_losses']),3)
	#print(single_loss_array)
	# Create a single figure for the heatmaps
	fig, ax = plt.subplots(1, 2, figsize=(10, 5))

	# Shared color scale
	vmin = min(
		np.nanmin(single_loss_array),
		np.nanmin(average_loss_array),
		#np.nanmin(max_loss_array),
	)
	vmax = max(
		np.nanmax(single_loss_array),
		np.nanmax(average_loss_array),
		#np.nanmax(max_loss_array),
	)
	norm = Normalize(vmin=vmin, vmax=vmax)

	# Plot the heatmaps
	titles = ["Trainng Loss", "Eval Loss", "Max Loss"]
	heatmaps = [single_loss_array, average_loss_array]#, max_loss_array]

	cmap = cm.plasma  # Choose a color map
	for ax, title, heatmap in zip(ax, titles, heatmaps):
		im = ax.imshow(heatmap, cmap=cmap, norm=norm, aspect='equal')
		# Add text annotations
		for i in range(heatmap.shape[0]):
			for j in range(heatmap.shape[1]):
				bg_color = im.cmap(im.norm(heatmap[i, j]))
				# Calculate luminance (using RGB luminance formula)
				luminance = 0.299 * bg_color[0] + 0.587 * bg_color[1] + 0.114 * bg_color[2]
				# Set text color based on luminance (high contrast)
				text_color = 'white' if luminance < 0.5 else 'black'
				ax.text(j, i, f'{heatmap[i, j]}', ha='center', va='center', color=text_color)
		# Label axes
		ax.set_xticks(range(len(node_counts)))
		ax.set_xticklabels(node_counts)
		ax.set_yticks(range(len(task_counts)))
		ax.set_yticklabels(task_counts)
		ax.set_title(title)
		ax.set_xlabel("Node Count")
		ax.set_ylabel("Task Count")
		#ax.set_xticklabels(node_counts)
		#ax.set_yticklabels(task_counts)
	# Add a colorbar
	
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
