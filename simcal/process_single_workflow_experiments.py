#!/usr/bin/env python3
import argparse
import sys

from Util import *
import matplotlib.pyplot as plt
from matplotlib import gridspec

def parse_command_line_arguments(program_name: str):
    epilog_string = ""

    parser = argparse.ArgumentParser(
        prog=program_name,
        description='Workflow simulator calibrator',
        epilog=epilog_string)

    try:
        # parser.add_argument('-cn', '--computer_name', type=str, metavar="<computer name>", required=True,
        #                     help='Name of this computer to add to the pickled file name')
        # parser.add_argument('-wn', '--workflow_name', type=str, metavar="<workflow names>", required=True,
        #                     help='Name of the workflow to run the calibration/validation on')
        # parser.add_argument('-ar', '--architecture', type=str,
        #                     metavar="[haswell|skylake|cascadelake]",
        #                     choices=['haswell', 'skylake', 'cascadelake'], required=True,
        #                     help='The computer architecture')
        # parser.add_argument('-al', '--algorithm', type=str,
        #                     metavar="[grid|random|gradient]",
        #                     choices=['grid', 'random', 'gradient'], required=True,
        #                     help='The calibration algorithm')
        # parser.add_argument('-tl', '--time_limit', type=int, metavar="<number of second>", required=True,
        #                     help='A training time limit, in seconds')
        # parser.add_argument('-th', '--num_threads', type=int, metavar="<number of threads (default=1)>", nargs='?',
        #                     default=1, help='A number of threads to use for training')
        # parser.add_argument('-lf', '--loss_function', type=str,
        #                     metavar="[mean_square_error, relative_average_error]",
        #                     choices=['mean_square_error', 'relative_average_error'], nargs='?',
        #                     default="relative_average_error",
        #                     help='The loss function to evaluate a calibration')
        # parser.add_argument('-cs', '--compute_service_scheme', type=str,
        #                     metavar="[all_bare_metal|htcondor_bare_metal]",
        #                     choices=['all_bare_metal', 'htcondor_bare_metal'], required=True,
        #                     help='The compute service scheme used by the simulator')
        # parser.add_argument('-ss', '--storage_service_scheme', type=str,
        #                     metavar="[submit_only|submit_and_compute_hosts]",
        #                     choices=['submit_only', 'submit_and_compute_hosts'], required=True,
        #                     help='The storage service scheme used by the simulator')
        # parser.add_argument('-ns', '--network_topology_scheme', type=str,
        #                     metavar="[one_link|one_and_then_many_links|many_links]",
        #                     choices=['one_link', 'one_and_then_many_links', 'many_links'], required=True,
        #                     help='The network topology scheme used by the simulator')

        return vars(parser.parse_args()), parser, None

    except argparse.ArgumentError as error:
        return None, parser, error


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
    # sys.stderr.write("Processing ")
    figure_name = f"figure-" \
                  f"{experiment_set.get_workflow()}-" \
                  f"{experiment_set.get_architecture()}-" \
                  f"{experiment_set.simulator.compute_service_scheme}-" \
                  f"{experiment_set.simulator.storage_service_scheme}-" \
                  f"{experiment_set.simulator.network_topology_scheme}-" \
                  f"{experiment_set.algorithm}-" \
                  f"{experiment_set.loss_function}-" \
                  f"{experiment_set.time_limit}-" \
                  f"{experiment_set.num_threads}.pdf"

    plt.figure().set_figwidth(20)
    plt.title(f"{experiment_set.get_workflow()} " \
              f"{experiment_set.get_architecture()} " \
              f"{experiment_set.simulator.compute_service_scheme} " \
              f"{experiment_set.simulator.storage_service_scheme} " \
              f"{experiment_set.simulator.network_topology_scheme} " \
              f"{experiment_set.algorithm} " \
              f"{experiment_set.loss_function} " \
              f"{experiment_set.time_limit} " \
              f"{experiment_set.num_threads}")

    to_plot = {}

    for result in experiment_set.experiments:
        if len(result.training_set_spec.cpu_values) == 1:
            kind = "one_cpu_one_data"
        elif len(result.training_set_spec.num_tasks_values) < max([len(x.num_tasks_values) for x in result.evaluation_set_specs]):
            kind = "num_tasks_generalization"
        elif len(result.training_set_spec.num_nodes_values) < max([len(x.num_nodes_values) for x in result.evaluation_set_specs]):
            kind = "num_nodes_generalization"
        else:
            kind = "training=eval"
        if kind not in to_plot:
            to_plot[kind] = []

        training_loss = result.calibration_loss
        training_spec = result.training_set_spec
        for i in range(0, len(result.evaluation_losses)):
            evaluation_loss = result.evaluation_losses[i]
            evaluation_spec = result.evaluation_set_specs[i]
            to_plot[kind].append((training_loss, evaluation_loss,
                            "T-"+build_label(training_spec)+"\nE-" + build_label(evaluation_spec)))

    to_plot = dict(sorted(to_plot.items()))

    width_ratios = [len(to_plot[kind]) / sum([len(to_plot[x]) for x in to_plot]) for kind in to_plot]
    spec = gridspec.GridSpec(ncols=len(width_ratios), nrows=1,
                             width_ratios=width_ratios, wspace=0.2,
                             hspace=0.1, height_ratios=[1])

    fig = plt.figure()
    fig.set_figheight(3)
    fig.set_figwidth(12)
    fontsize=7

    for i in range(0, len(to_plot)):
        ax = fig.add_subplot(spec[i])
        kind = list(to_plot.keys())[i]
        data = to_plot[kind]
        bar_width = 0.25
        multiplier = 0

        x_values = list(range(0, len(data)))
        offset = bar_width * multiplier
        ax.bar([x + offset for x in x_values],
                        [x for (x, y, z) in data],
                        bar_width,
                        label="calibration loss")
        # plt.bar_label(rects, padding=3)
        multiplier += 1
        offset = bar_width * multiplier
        ax.bar([x + offset for x in x_values],
                        [y for (x, y, z) in data],
                        bar_width,
                        label="evaluation loss")
        # plt.bar_label(rects, padding=3)
        ax.set_xticks(x_values, rotation=90, labels=[z for (x, y, z) in data])
        for label in (ax.get_xticklabels() + ax.get_yticklabels()):
            label.set_fontsize(fontsize)
        ax.set_title(kind, fontsize=fontsize)
        if i == 0:
            ax.legend(fontsize=fontsize)


    sys.stderr.write(f"Saving {figure_name}...\n")
    plt.savefig(figure_name, bbox_inches='tight')


def main():
    # Parse command-line arguments
    # args, parser, error = parse_command_line_arguments(sys.argv[0])
    # if not args:
    #     sys.stderr.write(f"Error: {error}\n")
    #     parser.print_usage()
    #     sys.exit(1)

    pickle_files = glob.glob("./pickled-*")
    sys.stderr.write(f"Found {len(pickle_files)} pickled files to process...\n")
    for pickle_file in pickle_files:
        with open(pickle_file, 'rb') as file:
            # sys.stderr.write(pickle_file + "\n")
            process_experiment_set(pickle.load(file))


if __name__ == "__main__":
    main()
