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
from collections import defaultdict
from matplotlib.gridspec import GridSpec


def process_experiment_group(base_data,times,workflow,extra,temporal_samples):
	name=workflow
	
		  #experiment_group[0].get_architecture(),
		  #experiment_group[0].simulator.compute_service_scheme,
		  #experiment_group[0].simulator.storage_service_scheme,
		  #experiment_group[0].simulator.network_topology_scheme,
		  #experiment_group[0].algorithm,
		  #experiment_group[0].loss_function,
		  #experiment_group[0].time_limit,
		  #experiment_group[0].num_threads
		  #]
	task_counts = set()
	node_counts = set()

	#print(name)
	# sys.stderr.write("Processing ")
	figure_name = f"figure-one_workflow_experiments-"+\
				name+extra+".pdf"

	
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
	for category in ["single_workflow","single_sample"]:
		for time in times:
			for node in base_data[category][time][workflow]:
				node_counts.add(node)
				for task in base_data[category][time][workflow][node]:
					task_counts.add(task)
					
	# Extract task and node counts
	task_counts = sorted(list(task_counts),reverse=True)
	node_counts = sorted(list(node_counts))
	#print(name)
	#print(task_counts)
	#print(node_counts)
	# Initialize arrays for the heatmaps
	substitute={"single_workflow":"Rectangular Sample","single_sample":"Single Sample"}
	max_loss_array = np.full((len(task_counts), len(node_counts)), np.nan)
	heatmaps=[]
	subtitles=[]
	temporal=[]
	t_ticks=[]
	for time in base_data["single_workflow"].keys():
		if workflow in base_data["single_workflow"][time]:
			try:
				temporal.append(round(np.mean(base_data["single_workflow"][time][workflow][node_counts[temporal_samples[0]]][task_counts[temporal_samples[1]]]['evaluation_losses']),3))
				t_ticks.append(round(time/60))
			except:
				pass
	# Populate arrays with data
	for time in times: 
		for category in ["single_sample","single_workflow"]:
			data=base_data[category][time][workflow]
			sdata = np.full((len(task_counts), len(node_counts)), np.nan)
			for i, task in enumerate(task_counts):
				for j, node in enumerate(node_counts):
					if node in data.keys() and task in data[node]:
						entry = data[node][task]
						sdata[i, j] = round(np.mean(entry['evaluation_losses']),3)
			heatmaps.append(sdata)
			subtitles.append(f"{substitute[category]} at {time/60} Minutes")
	#print(single_loss_array)
	# Create a single figure for the heatmaps
	fig = plt.figure(figsize=(13, 10))
	gs = GridSpec(2, 3, figure=fig,width_ratios=[4,4,1])
	
	ax1 = fig.add_subplot(gs[0, 0])
	ax2 = fig.add_subplot(gs[0, 1])
	ax3 = fig.add_subplot(gs[1, 0])
	ax4 = fig.add_subplot(gs[1, 1])
	ax5 = fig.add_subplot(gs[:, 2])
	#fig, axl = plt.subplots(2, 3, figsize=(10, 15))
	titles = subtitles

	#print(heatmaps)
	# Shared color scale
	# Shared color scale
	vmin = min(np.nanmin(heatmaps),np.nanmin(temporal))
	vmax = max(np.nanmax(heatmaps),np.nanmax(temporal))
	norm = Normalize(vmin=vmin, vmax=vmax)
	#print(vmin,vmax)
	# Plot the heatmaps
	
	cmap = cm.plasma_r  # Choose a color map
	for ax, title, heatmap in zip([ax1,ax2,ax3,ax4], titles, heatmaps):
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
	
	ax = ax5  # Use the top-right position for the new heatmap
	new_heatmap = np.expand_dims(temporal, axis=1)  # Turn the 1D array into a column vector
	im = ax.imshow(new_heatmap, cmap=cmap, norm=norm, aspect='auto')  # 'auto' ensures it stretches correctly
	for i in range(new_heatmap.shape[0]):
		bg_color = im.cmap(im.norm(new_heatmap[i, 0]))  # Only one column, so index 0
		luminance = 0.299 * bg_color[0] + 0.587 * bg_color[1] + 0.114 * bg_color[2]
		text_color = 'white' if luminance < 0.5 else 'black'
		ax.text(0, i, f'{new_heatmap[i, 0]}', ha='center', va='center', color=text_color)

	ax.set_xticks([0])  # Only one tick, since it's a single column
	ax.set_xticklabels([''])  # Empty, as it's a single column
	ax.set_yticks(range(len(temporal)))  # Set y-ticks based on the number of data points
	ax.set_yticklabels(t_ticks)  # Set the y-tick labels to the values of the 1D array
	ax.set_title("Error over Time")  # Customize the title as needed
	ax.set_xlabel("")
	ax.set_ylabel("Minutes")
	# Add a colorbar
	fig.colorbar(cm.ScalarMappable(norm=norm, cmap=cmap), ax=ax, orientation='vertical', fraction=0.02, pad=0.04)
	plt.suptitle(name)
	sys.stderr.write(f"Saving {figure_name}...\n")
	plt.savefig(figure_name, bbox_inches='tight')
	plt.close()
	return name,data
from heatmapdata import *
def main():
	parser = argparse.ArgumentParser()
	parser.add_argument("top", type=int, help="time used for top graphs")
	parser.add_argument("bottom", type=int, help="time used for bottom graphs")

	args = parser.parse_args()
	alldata=[data,data47]
	extra=["","-47"]
	for datum,ex in zip(alldata,extra):
		names=set()
		for category in ["single_sample","single_workflow"]:
			for time in [args.top,args.bottom]:
				for workflow in datum[category][time]:
					#print(workflow)
					names.add(workflow)	
		names=sorted(list(names))
		for workflow in names:
			try:
				process_experiment_group(datum,[args.top,args.bottom],workflow,ex, [2,2])
			except:
				print("failed to plot "+workflow)
if __name__ == "__main__":
	main()
