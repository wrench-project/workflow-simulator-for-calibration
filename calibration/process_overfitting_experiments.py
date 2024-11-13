#!/usr/bin/env python3
import argparse
import sys
from glob import glob
import pickle 

import matplotlib.pyplot as plt
from matplotlib import gridspec

from Util import *





def process_experiment_sets(pickle_files):
	largest_value = 0
	to_plot = []
	for pickle_file in pickle_files:
		with open(pickle_file, 'rb') as file:
			# sys.stderr.write(pickle_file + "\n")
			experiment_set=pickle.load(file)

		if experiment_set.is_empty():
			return 

		# sys.stderr.write("Processing ")
		figure_name = f"figure-overfitting-expiriments.pdf"

		plt.title(f"overfitting expiriments")
		for result in experiment_set.experiments:
			training_loss = result.calibration_loss
			training_spec = result.training_set_spec
			for i in range(0, len(result.evaluation_losses)):
				evaluation_loss = result.evaluation_losses[i]
				evaluation_spec = result.evaluation_set_specs[i]
				

				largest_value = max(largest_value, max(training_loss, evaluation_loss))

				to_plot.append((training_loss,
									  f"{experiment_set.algorithm} {experiment_set.loss_function} {experiment_set.loss_aggregator}"))

	to_plot = sorted(to_plot)
	#print(to_plot)
	total_num_results = len(to_plot) 

	
	print(to_plot)
	spec = gridspec.GridSpec(ncols=1, nrows=1, wspace=0.2,
							 hspace=0.1, height_ratios=[1])

	#temp = max([len(x) for x in to_plot.values()])
	#biggest_kind = to_plot[0]

	fig = plt.figure()
	fig.set_figheight(3)
	fig.set_figwidth(max(10, total_num_results))
	fontsize = 7

	ax = fig.add_subplot(spec[i])
	#kind = list(to_plot.keys())[i]
	data = to_plot
	bar_width = 0.25
	multiplier = 0
	ax.grid(axis='y')
	ax.set_axisbelow(True)

	x_values = list(range(0, len(data)))
	offset = bar_width * multiplier
	ax.bar([x + offset - bar_width / 2 for x in x_values],
		   [x for (x, z) in data],
		   bar_width,
		   label="calibration loss")
	# plt.bar_label(rects, padding=3)
	multiplier += 1
	offset = bar_width * multiplier
	# plt.bar_label(rects, padding=3)
	ax.set_xticks(x_values, rotation=90, labels=[z for (x,  z) in data])
	for label in (ax.get_xticklabels() + ax.get_yticklabels()):
		label.set_fontsize(fontsize)

	ax.set_ylim([0, largest_value * 1.05])
		#ax.set_title(kind, fontsize=fontsize)
		#if kind == biggest_kind:
		#	ax.legend(fontsize=fontsize)

	sys.stderr.write(f"Saving {figure_name}...\n")
	plt.savefig(figure_name, bbox_inches='tight')
	plt.close()


def main():
	pickle_files = glob("./pickled-one_calibration-*")
	sys.stderr.write(f"Found {len(pickle_files)} pickled files to process...\n")
	process_experiment_sets(pickle_files)


if __name__ == "__main__":
	main()
