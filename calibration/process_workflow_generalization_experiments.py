#!/usr/bin/env python3
import argparse
import sys
from glob import glob

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

    training_workflow = None
    eval_workflow = None
    for result in experiment_set.experiments:
        if training_workflow is None:
            training_workflow = result.training_set_spec.workflow_name
        elif training_workflow != result.training_set_spec.workflow_name:
            raise Exception("Different results in experiment set have different training workflows!!")
        if eval_workflow is None:
            eval_workflow = result.evaluation_set_specs[0].workflow_name
        elif eval_workflow != result.evaluation_set_specs[0].workflow_name:
            raise Exception("Different results in experiment set have different eval workflows!!")

    # sys.stderr.write("Processing ")
    figure_name = f"figure-workflow_generalization_experiments-" \
                  f"{training_workflow}-" \
                  f"{eval_workflow}-" \
                  f"{experiment_set.get_architecture()}-" \
                  f"{experiment_set.simulator.compute_service_scheme}-" \
                  f"{experiment_set.simulator.storage_service_scheme}-" \
                  f"{experiment_set.simulator.network_topology_scheme}-" \
                  f"{experiment_set.algorithm}-" \
                  f"{experiment_set.loss_function}-" \
                  f"{experiment_set.time_limit}-" \
                  f"{experiment_set.num_threads}.pdf"

    plt.title(f"{training_workflow} " \
              f"{eval_workflow} " \
              f"{experiment_set.get_architecture()} " \
              f"{experiment_set.simulator.compute_service_scheme} " \
              f"{experiment_set.simulator.storage_service_scheme} " \
              f"{experiment_set.simulator.network_topology_scheme} " \
              f"{experiment_set.algorithm} " \
              f"{experiment_set.loss_function} " \
              f"{experiment_set.time_limit} " \
              f"{experiment_set.num_threads}")

    to_plot = []
    largest_value = 0

    for result in experiment_set.experiments:
        training_loss = result.calibration_loss
        training_spec = result.training_set_spec
        evaluation_loss = result.evaluation_losses[0]

        to_plot.append((training_loss, evaluation_loss,
                        "T-" + build_label(training_spec) + "\nE-" + eval_workflow))

    fig = plt.figure()
    fig.set_figheight(3)
    fig.set_figwidth(10)
    ax = fig.add_subplot()
    fontsize = 7

    bar_width = 0.25
    multiplier = 0
    plt.grid(axis='y')
    ax.set_axisbelow(True)

    x_values = list(range(0, len(to_plot)))
    offset = bar_width * multiplier
    ax.bar([x + offset - bar_width / 2 for x in x_values],
           [x for (x, y, z) in to_plot],
           bar_width,
           label="calibration loss")
    # plt.bar_label(rects, padding=3)
    multiplier += 1
    offset = bar_width * multiplier
    ax.bar([x + offset - bar_width / 2 for x in x_values],
           [y for (x, y, z) in to_plot],
           bar_width,
           label="evaluation loss")
    # plt.bar_label(rects, padding=3)
    ax.set_xticks(x_values, rotation=90, labels=[z for (x, y, z) in to_plot])
    for label in (ax.get_xticklabels() + ax.get_yticklabels()):
        label.set_fontsize(fontsize)

    ax.legend(fontsize=fontsize)

    sys.stderr.write(f"Saving {figure_name}...\n")
    plt.savefig(figure_name, bbox_inches='tight')
    plt.close()


def main():
    pickle_files = glob("./pickled-workflow_generalization_experiments-*")
    sys.stderr.write(f"Found {len(pickle_files)} pickled files to process...\n")
    for pickle_file in pickle_files:
        with open(pickle_file, 'rb') as file:
            # sys.stderr.write(pickle_file + "\n")
            process_experiment_set(pickle.load(file))


if __name__ == "__main__":
    main()
