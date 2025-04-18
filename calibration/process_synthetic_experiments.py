#!/usr/bin/env python3
import argparse
import sys
from glob import glob
import pickle 
import json 
import matplotlib.pyplot as plt
from matplotlib import gridspec

from Util import *



def process_experiment_sets(pickle_files, calibration, threshold1, threshold2):
	#largest_value = 0
	to_plot = []
	
	loss=LossHandler("makespan","average_error")
	# Load and categorize experiment data
	for pickle_file in pickle_files:
		with open(pickle_file, 'rb') as file:
			experiment_set = pickle.load(file)

		if experiment_set.is_empty():
			return 
		for experiment in experiment_set.experiments:
			#print(dir(experiment.training_set_spec))
		
			experiment.training_set_spec.update_fields()
			#print(experiment.training_set_spec.workflow_name)
			resl=0
			for parameter in experiment.calibration.values():
				#print (calibration)
				partial=json.loads(calibration)
				#print (partial)
				#print(parameter)
				for key in parameter.parameter.custom_data:
					
					partial=partial[key]
					
				resl+=abs(relative_error(parseDoubleUnited(partial),parameter.value))
			label = f"{experiment_set.algorithm} {experiment_set.loss_function} {experiment_set.loss_aggregator}"
			to_plot.append((resl,label))
	# Sort data within each category
	to_plot = sorted(to_plot)
	print(to_plot)
	
	# Calculate dynamic widths for each subplot
	bar_width = 0.25
	
	fig_width = max(10, len(to_plot) * bar_width * 2)
	fig_height = 6  # Fixed height
	# Create figure with 3 subplots and set dynamic widths
	fig, ax = plt.subplots(figsize=(fig_width, fig_height))
	fontsize = 7

	ax.set_title(f"Synthetic", fontsize=fontsize + 2)
	
	if to_plot:
		# Extract x_values, heights, and labels from the data
		x_values = list(range(len(to_plot)))
		heights = [x for (x, _) in to_plot]
		labels = [z for (_, z) in to_plot]

		# Create the bar plot
		ax.bar(x_values, heights, bar_width, label="Calibration Loss")

		# Set x-ticks and labels
		ax.set_xticks(x_values)
		ax.set_xticklabels(labels, rotation=90, fontsize=fontsize)

		# Adjust y-axis limit slightly above the max value
		largest_value = max(heights)
		ax.set_ylim([0, largest_value * 1.05])

		# Set grid and aesthetics
		ax.grid(axis='y', linestyle='--', alpha=0.7)
		ax.set_axisbelow(True)

		# Title and label
		ax.set_title("Synthetic Calibrations", fontsize=fontsize + 2)
		ax.set_ylabel("Parameter Loss", fontsize=fontsize)
	else:
		# Display "No Data" message if to_plot is empty
		ax.text(0.5, 0.5, "No Data", ha='center', va='center', fontsize=fontsize + 2)
		ax.axis('off')  # Hide axes

	# Save the figure
	figure_name = "figure-synthetic-experiments.pdf"
	sys.stderr.write(f"Saving {figure_name}...\n")
	#plt.tight_layout()
	plt.savefig(figure_name, bbox_inches='tight')
	plt.close()


def main(args):
	
	pickle_files = []
	for pattern in args['pickle_files']:
		if '*' in pattern or '?' in pattern:
			pickle_files += glob(pattern)
		else:
			pickle_files.append(pattern)
	
	sys.stderr.write(f"Found {len(pickle_files)} pickled files to process...\n")
	process_experiment_sets(pickle_files, args["simulator_args"], 50, 1000)


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="Process experiment pickle files and generate a plot.")
	parser.add_argument('-a', '--simulator_args', default='{"workflow":{"file":"\'$file\'","reference_flops":"100Mf"},"error_computation_scheme":"makespan","error_computation_scheme_parameters":{"makespan":{}},"scheduling_overhead":"10ms","compute_service_scheme":"htcondor_bare_metal","compute_service_scheme_parameters":{"all_bare_metal":{"submit_host":{"num_cores":"16","speed":"12345Gf"},"compute_hosts":{"num_cores":"16","speed":"1f"},"properties":{"BareMetalComputeServiceProperty::THREAD_STARTUP_OVERHEAD":"42s"},"payloads":{}},"htcondor_bare_metal":{"submit_host":{"num_cores":"1231","speed":"123Gf"},"compute_hosts":{"num_cores":"16","speed":"982452266.749154f"},"bare_metal_properties":{"BareMetalComputeServiceProperty::THREAD_STARTUP_OVERHEAD":"3.045662s"},"bare_metal_payloads":{},"htcondor_properties":{"HTCondorComputeServiceProperty::NEGOTIATOR_OVERHEAD":"12.338810s","HTCondorComputeServiceProperty::GRID_PRE_EXECUTION_DELAY":"14.790155s","HTCondorComputeServiceProperty::GRID_POST_EXECUTION_DELAY":"14.079311s"},"htcondor_payloads":{}}},"storage_service_scheme":"submit_and_compute_hosts","storage_service_scheme_parameters":{"submit_only":{"bandwidth_submit_disk_read":"10000MBps","bandwidth_submit_disk_write":"10000MBps","submit_properties":{"StorageServiceProperty::BUFFER_SIZE":"42MB","SimpleStorageServiceProperty::MAX_NUM_CONCURRENT_DATA_CONNECTIONS":"8"},"submit_payloads":{}},"submit_and_compute_hosts":{"bandwidth_submit_disk_read":"428823427550.539185bps","bandwidth_submit_disk_write":"4398215356.339356bps","submit_properties":{"StorageServiceProperty::BUFFER_SIZE":"42000000","SimpleStorageServiceProperty::MAX_NUM_CONCURRENT_DATA_CONNECTIONS":"59"},"submit_payloads":{},"bandwidth_compute_host_disk_read":"28687530839.627506bps","bandwidth_compute_host_write":"24561408103.754391bps","compute_host_properties":{"StorageServiceProperty::BUFFER_SIZE":"1048576B","SimpleStorageServiceProperty::MAX_NUM_CONCURRENT_DATA_CONNECTIONS":"28"},"compute_host_payloads":{}}},"network_topology_scheme":"one_and_then_many_links","network_topology_scheme_parameters":{"one_link":{"bandwidth":"4MBps","latency":"10us"},"many_links":{"bandwidth_submit_to_compute_host":"4000MBps","latency_submit_to_compute_host":"10us"},"one_and_then_many_links":{"bandwidth_out_of_submit":"16226331284.128448bps","latency_out_of_submit":"0.009044s","bandwidth_to_compute_hosts":"11195981534.552021bps","latency_to_compute_hosts":"10us","latency_submit_to_compute_host":"0.008494s"}}}', type=str, metavar="<json args>",
						help="JSON string of arguments used to generate synthetic data")
	parser.add_argument('pickle_files', nargs='+', type=str, metavar="<pickle files>",
						help="List of pickle files or patterns to process. Supports wildcards.")					
	args = vars(parser.parse_args())

	main(args)
