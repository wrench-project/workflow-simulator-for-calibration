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
from heatmapdata import *
def avg(l):
	return sum(l)/len(l)
def process_experiment_group(base_data,times,workflows,extra,interest_point):
	name="all"
	colors = ['red', 'orange','yellow','green','blue'  ]
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
	figure_name = f"pointclouds-"+\
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
	x_vals = []
	y_vals = []
	for i,time in enumerate(times):
		for j,dataset in enumerate(data):
			cores_v=set()
			tasks_v=set()
			for c,workflow in enumerate(workflows):
				for cores, inner_dict in data[dataset][time][workflow].items():
					cores_v.add(cores)
					for tasks, obj in inner_dict.items():
						tasks_v.add(tasks)
						x_vals.append(avg(obj["evaluation_losses"]))
						y_vals.append(obj["machine_time"])
	xscale=(min(x_vals),max(x_vals))
	yscale=(min(y_vals),max(y_vals))
	xsize=(xscale[1]-xscale[0])
	ysize=(yscale[1]-yscale[0])
	xscale=(xscale[0]-xsize*.1,xscale[1]+xsize*.1)
	yscale=(yscale[0]-ysize*.1,yscale[1]+ysize*.1)
	fig, axes = plt.subplots(1,1, figsize=(12, 10))
	for i,time in enumerate(times):
		ax = axes
		for c,workflow in enumerate(workflows):
			x_vals = []
			y_vals = []
			for j,dataset in enumerate(data):
				cores_v=set()
				tasks_v=set()
				for cores, inner_dict in data[dataset][time][workflow].items():
					cores_v.add(cores)
					for tasks, obj in inner_dict.items():
						tasks_v.add(tasks)
						x_vals.append(avg(obj["evaluation_losses"]))
						y_vals.append(obj["machine_time"])
				#print(time,dataset,workflow,cores_v)
				cores_v=sorted(list(cores_v))[interest_point[0]]
				#print(time,dataset,workflow,tasks_v)
				tasks_v=sorted(list(tasks_v))[interest_point[1]]
				ax.scatter(x_vals, y_vals,color=colors[c],s=5)
				if dataset=="single_sample":
					ax.scatter([data[dataset][time][workflow][cores_v][tasks_v]["evaluation_losses"]], 
					[data[dataset][time][workflow][cores_v][tasks_v]["machine_time"]],color=colors[c],marker='s')
				
	plt.xlim(*xscale)
	plt.ylim(*yscale)
			
			

	plt.suptitle(name)
	sys.stderr.write(f"Saving {figure_name}...\n")
	plt.grid(True)
	plt.savefig(figure_name, bbox_inches='tight')
	plt.close()
	#return name,data

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
		#for workflow in names:
		#	if workflow in ["chain","forkjoin"]:
		#		continue
			#try:
		names.remove("chain")
		names.remove("forkjoin")
		process_experiment_group(datum,[86400],names,ex,[2,2])
			#except:
			#	print("failed to plot "+workflow)
if __name__ == "__main__":
	main()
