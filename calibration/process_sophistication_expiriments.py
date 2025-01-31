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
	bdata=dict(to_plot)


	categories = []
	training_losses = []
	evaluation_losses = []
	data=[]
	for system, modes in bdata.items():
		for mode, links in modes.items():
			for link, metrics in links.items():
				categories.append((system,mode,link))
				training_losses.append(metrics['training_loss'])
				evaluation_losses.append(metrics['evaluation_losses'])
				data.append((system,link,mode,metrics['evaluation_losses']))
	# Plot
	#fig, axs = plt.subplots(1, 1, figsize=(5, 5), sharex=True)

	#print(categories)
	# Evaluation Loss
	
	
	# Define colors based on third element
	color_map = {"submit_only": "lightblue", "submit_and_compute_hosts": "lightgreen"}
	
	# Extract unique group names
	main_groups = list(set(row[0] for row in data))  # First label
	main_groups.sort()
	sub_groups = list(set(row[1] for row in data))  # Second label
	sub_groups.sort()

	# Organizing y-positions
	y_positions = []
	y_labels = []
	bars = []
	y_offset = 0
	sep_big = 2  # Double line separator
	sep_small = 1  # Single line separator

	for main_group in main_groups:
		for sub_group in sub_groups:
			for row in data:
				if row[0] == main_group and row[1] == sub_group:
					y_positions.append(y_offset)
					bars.append(row)  # Store data for plotting
					y_labels.append(f"{row[0]} - {row[1]} ({row[2]})")
					y_offset += 1  # Move y position
					print((name[0],*row),',')
			
			#y_offset += sep_small  # Space between sub-groups
		
		 #y_offset += sep_big  # Space between main groups

	# Create the figure
	fig, ax = plt.subplots(figsize=(8, 6))

	# Plot the bars
	for i, (main_group, sub_group, color_label, value) in enumerate(bars):
		ax.barh(y_positions[i], value, color=color_map[color_label])

	# Formatting
	ax.set_yticks(y_positions)
	ax.set_yticklabels(y_labels)

	# Add grid lines for separation
	for y in y_positions[1::2]:
		ax.axhline(y + 0.5, color="black", linewidth=0.5)  # Normal separator

	# Extra thick lines for major groups
	y_major_separators = [y for y in y_positions if y in np.cumsum([len([r for r in data if r[0] == g]) for g in main_groups])]
	for y in y_major_separators:
		ax.axhline(y - 0.5, color="black", linewidth=2)  # Thick separator

	# Labels and title
	plt.xlabel("Value")
	plt.title("Sophistication: "+" ".join(name))
	plt.gca().invert_yaxis()  # Align with barh convention
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
