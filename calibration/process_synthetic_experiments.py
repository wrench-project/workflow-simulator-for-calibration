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


def main():
	parser = argparse.ArgumentParser(description="Process experiment pickle files and generate a plot.")
	parser.add_argument('-a ', '--simulator_args', type=str, metavar="<json args>", 
						help='Json string of arguments used to generate synthetic data')
	args = vars(parser.parse_args())

	pickle_files = glob("./pickled-one_calibration-*")
	sys.stderr.write(f"Found {len(pickle_files)} pickled files to process...\n")
	process_experiment_sets(pickle_files, args["simulator_args"], 50, 1000)


if __name__ == "__main__":
	main()
