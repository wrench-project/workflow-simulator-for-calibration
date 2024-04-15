#!/usr/bin/env python3
import os
import glob
import argparse

from Util import *


def relative_average_error(x: List[float], y: List[float]):
    return sum([abs(a - b) / a for (a, b) in list(zip(x, y))]) / len(x)


def parse_command_line_arguments(program_name: str):
    epilog_string = f"""Example:
python3 {program_name} --workflow_dir ../JSONS/ --workflow_name seismology --architecture cascadelake  
"""

    parser = argparse.ArgumentParser(
        prog=program_name,
        description='Workflow simulator calibrator',
        epilog=epilog_string)

    parser.add_argument('-wd', '--workflow_dir', type=str, metavar="<workflow dir>", required=True,
                        help='Directory that contains all workflow instances')

    parser.add_argument('-wn', '--workflow_name', type=str, metavar="<workflow name>", required=True,
                        help='Workflow name')
    parser.add_argument('-df', '--data_footprint', type=str, nargs="?", default="*",
                        help='The workflow data footprint')
    parser.add_argument('-cw', '--cpu_work', type=str, nargs="?", default="*",
                        help='The workflow CPU work')
    parser.add_argument('-ns', '--architecture', type=str,
                        metavar="[haswell|skylake|cascadelake]",
                        choices=['haswell', 'skylake', 'cascadelake'], required=True,
                        help='The computer architecture')
    parser.add_argument('-nc', '--num_compute_nodes', type=str, nargs="?", default="*",
                        help='The workflow execution number of compute nodes')

    parser.add_argument('-a', '--algorithm', type=str,
                        metavar="[grid|random|gradient]",
                        choices=['grid', 'random', 'gradient'], required=True,
                        help='The calibration algorithm')
    parser.add_argument('-tl', '--time_limit', type=str, metavar="<number of second>", required=True,
                        help='A training time limit, in seconds')
    parser.add_argument('-th', '--num_threads', type=str, metavar="<number of threads (default=1)>", nargs='?',
                        default=1, help='A number of threads to use for training')
    parser.add_argument('-lf', '--loss_function', type=str,
                        metavar="[mean_square_error]",
                        choices=['mean_square_error','relative_average_error'], nargs='?', default="mean_square_error",
                        help='The loss function to evaluate a calibration')

    args = vars(parser.parse_args())
    return args


def main():
    # Parse command-line arguments
    args = parse_command_line_arguments(sys.argv[0])

    # Fill in arguments that are not passed
    args["cpu_fraction"] = "0.6"
    args["num_tasks"] = "*"

    # Instantiate a simulator object
    simulator = Simulator()

    # Build list of workflows
    search_string = f"{args['workflow_dir']}/" \
                    f"{args['workflow_name']}-" \
                    f"{args['num_tasks']}-" \
                    f"{args['cpu_work']}-" \
                    f"{args['cpu_fraction']}-" \
                    f"{args['data_footprint']}-" \
                    f"{args['architecture']}-" \
                    f"{args['num_compute_nodes']}-*.json"

    workflows = glob.glob(search_string)
    if len(workflows) == 0:
        sys.stderr.write(f"No workflow found ({search_string})\n")
        sys.exit(1)

    workflows = [os.path.abspath(x) for x in workflows]

    # Build dictionary based on number of tasks
    workflow_dict = {}
    for workflow in workflows:
        num_tasks = int(workflow.split("-")[1])
        if num_tasks not in workflow_dict:
            workflow_dict[num_tasks] = []
        workflow_dict[num_tasks].append(workflow)

    keys = sorted(list(workflow_dict.keys()))
    print(keys)
    for i in range(1, len(workflow_dict)):
        training_workflows = []
        for key in keys[0:i]:
            training_workflows += workflow_dict[key]
        sys.stderr.write(f"Training on {len(training_workflows)} workflows with #tasks: {keys[0:i]} ...\n")

        calibration, loss = compute_calibration(training_workflows,
                                                args["algorithm"],
                                                simulator,
                                                "all_bare_metal",
                                                "submit_only",
                                                "one_link",
                                                "mean_square_error",
                                                float(args["time_limit"]),
                                                int(args["num_threads"]))
        sys.stderr.write(f"  calibration loss: {loss}\n")

        sys.stderr.write(f"Evaluating calibration on {len(workflow_dict[keys[-1]])} workflows with {keys[-1]} tasks...\n")
        evaluation_loss = evaluate_calibration(workflow_dict[keys[-1]],
                                               simulator,
                                               calibration,
                                               "mean_square_error")
        sys.stderr.write(f"  evaluation loss: {evaluation_loss}\n")


if __name__ == "__main__":
    main()
