#!/usr/bin/env python3
import argparse
import sys
from glob import glob
import pickle 

import matplotlib.pyplot as plt
from matplotlib import gridspec

from Util import *


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


def process_experiment_set(experiment_set: ExperimentSet):
    if experiment_set.is_empty():
        return

    # sys.stderr.write("Processing ")
    figure_name = f"figure-one_workflow_experiments-" \
                  f"{experiment_set.get_workflow()}-" \
                  f"{experiment_set.get_architecture()}-" \
                  f"{experiment_set.simulator.compute_service_scheme}-" \
                  f"{experiment_set.simulator.storage_service_scheme}-" \
                  f"{experiment_set.simulator.network_topology_scheme}-" \
                  f"{experiment_set.algorithm}-" \
                  f"{experiment_set.loss_function}-" \
                  f"{experiment_set.time_limit}-" \
                  f"{experiment_set.num_threads}.pdf"

    plt.title(f"{experiment_set.get_workflow()} "
              f"{experiment_set.get_architecture()} "
              f"{experiment_set.simulator.compute_service_scheme} "
              f"{experiment_set.simulator.storage_service_scheme} "
              f"{experiment_set.simulator.network_topology_scheme} "
              f"{experiment_set.algorithm} "
              f"{experiment_set.loss_function} "
              f"{experiment_set.time_limit} "
              f"{experiment_set.num_threads}")

    to_plot = {}
    largest_value = 0

    for result in experiment_set.experiments:
        training_loss = result.calibration_loss
        training_spec = result.training_set_spec
        for i in range(0, len(result.evaluation_losses)):
            evaluation_loss = result.evaluation_losses[i]
            evaluation_spec = result.evaluation_set_specs[i]
            if len(training_spec.cpu_values) == 1:
                kind = "one_cpu_one_data"
            elif training_spec.num_tasks_values != evaluation_spec.num_tasks_values:
                kind = "num_tasks_generalization"
            elif training_spec.num_nodes_values != evaluation_spec.num_nodes_values:
                kind = "num_nodes_generalization"
            else:
                kind = "training=eval"
            if kind not in to_plot:
                to_plot[kind] = []

            largest_value = max(largest_value, max(training_loss, evaluation_loss))

            to_plot[kind].append((training_loss, evaluation_loss,
                                  "T-" + build_label(training_spec) + "\nE-" + build_label(evaluation_spec)))

    to_plot = dict(sorted(to_plot.items()))
    total_num_results = sum([len(to_plot[x]) for x in to_plot])

    width_ratios = [len(to_plot[kind]) / total_num_results for kind in to_plot]
    spec = gridspec.GridSpec(ncols=len(width_ratios), nrows=1,
                             width_ratios=width_ratios, wspace=0.2,
                             hspace=0.1, height_ratios=[1])

    temp = max([len(x) for x in to_plot.values()])
    biggest_kind = [key for key in to_plot if len(to_plot[key]) == temp][0]

    fig = plt.figure()
    fig.set_figheight(3)
    fig.set_figwidth(max(10, total_num_results))
    fontsize = 7

    for i in range(0, len(to_plot)):
        ax = fig.add_subplot(spec[i])
        kind = list(to_plot.keys())[i]
        data = to_plot[kind]
        bar_width = 0.25
        multiplier = 0
        ax.grid(axis='y')
        ax.set_axisbelow(True)

        x_values = list(range(0, len(data)))
        offset = bar_width * multiplier
        ax.bar([x + offset - bar_width / 2 for x in x_values],
               [x for (x, y, z) in data],
               bar_width,
               label="calibration loss")
        # plt.bar_label(rects, padding=3)
        multiplier += 1
        offset = bar_width * multiplier
        ax.bar([x + offset - bar_width / 2 for x in x_values],
               [y for (x, y, z) in data],
               bar_width,
               label="evaluation loss")
        # plt.bar_label(rects, padding=3)
        ax.set_xticks(x_values, rotation=90, labels=[z for (x, y, z) in data])
        for label in (ax.get_xticklabels() + ax.get_yticklabels()):
            label.set_fontsize(fontsize)

        ax.set_ylim([0, largest_value * 1.05])
        ax.set_title(kind, fontsize=fontsize)
        if kind == biggest_kind:
            ax.legend(fontsize=fontsize)

    sys.stderr.write(f"Saving {figure_name}...\n")
    plt.savefig(figure_name, bbox_inches='tight')
    plt.close()


def main():
    pickle_files = glob("./pickled-one_workflow_experiments-*")
    sys.stderr.write(f"Found {len(pickle_files)} pickled files to process...\n")
    for pickle_file in pickle_files:
        with open(pickle_file, 'rb') as file:
            # sys.stderr.write(pickle_file + "\n")
            process_experiment_set(pickle.load(file))


if __name__ == "__main__":
    main()
