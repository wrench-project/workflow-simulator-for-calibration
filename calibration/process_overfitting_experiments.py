#!/usr/bin/env python3
import argparse
import sys
from glob import glob
import pickle 

import matplotlib.pyplot as plt
from matplotlib import gridspec

from Util import *



def process_experiment_sets(pickle_files, threshold1, threshold2):
	#largest_value = 0
	to_plot_low = []
	to_plot_medium = []
	to_plot_high = []
	loss=LossHandler("makespan","average")
	# Load and categorize experiment data
	for pickle_file in pickle_files:
		with open(pickle_file, 'rb') as file:
			experiment_set = pickle.load(file)

		if experiment_set.is_empty():
			return 

		for result in experiment_set.experiments:
			for output in result.evaluation_makespans:
				training_loss = loss(output)
				label = f"{experiment_set.algorithm} {experiment_set.loss_function} {experiment_set.loss_aggregator}"
				# = max(largest_value, training_loss)

				# Categorize data based on thresholds
				if training_loss < threshold1:
					to_plot_low.append((training_loss, label))
				elif training_loss < threshold2:
					to_plot_medium.append((training_loss, label))
				else:
					to_plot_high.append((training_loss, label))

	# Sort data within each category
	to_plot_low = sorted(to_plot_low)
	to_plot_medium = sorted(to_plot_medium)
	to_plot_high = sorted(to_plot_high)

	# Calculate dynamic widths for each subplot
	bar_width = 0.25
	num_items = [len(to_plot_low), len(to_plot_medium), len(to_plot_high)]
	fig_width = sum(max(10, count * bar_width * 2) for count in num_items)

	# Create figure with 3 subplots and set dynamic widths
	fig = plt.figure(figsize=(fig_width, 3))
	gs = gridspec.GridSpec(1, 3, width_ratios=num_items) 
	plots = [to_plot_low, to_plot_medium, to_plot_high]
	titles = ['Low', 'Medium', 'High']
	fontsize = 7

	for i, data in enumerate(plots):
		ax = fig.add_subplot(gs[i])
		ax.set_title(f"{titles[i]} Range", fontsize=fontsize + 2)
		
		if data:
			x_values = list(range(len(data)))
			ax.bar(x_values, [x for (x, _) in data], bar_width, label="calibration loss")
			ax.set_xticks(x_values)
			ax.set_xticklabels([z for (_, z) in data], rotation=90)
			largest_value=max([x for (x, _) in data])
			ax.set_ylim([0, largest_value * 1.05])

			for label in (ax.get_xticklabels() + ax.get_yticklabels()):
				label.set_fontsize(fontsize)

			ax.grid(axis='y')
			ax.set_axisbelow(True)
		else:
			ax.text(0.5, 0.5, "No Data", ha='center', va='center', fontsize=fontsize + 2)

	# Save the figure
	figure_name = "figure-overfitting-experiments.pdf"
	sys.stderr.write(f"Saving {figure_name}...\n")
	#plt.tight_layout()
	plt.savefig(figure_name, bbox_inches='tight')
	plt.close()


def main():
	parser = argparse.ArgumentParser(description="Process experiment pickle files and generate a plot.")
	
	args = parser.parse_args()

	pickle_files = glob("./pickled-one_calibration-*")
	sys.stderr.write(f"Found {len(pickle_files)} pickled files to process...\n")
	process_experiment_sets(pickle_files, 50, 1000)


if __name__ == "__main__":
	main()
