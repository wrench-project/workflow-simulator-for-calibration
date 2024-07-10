#!/usr/bin/env python3
import argparse
from datetime import timedelta
from scipy.stats import variation
import time
from Util import *
import json





def parse_command_line_arguments(program_name: str):
    epilog_string = ""

    parser = argparse.ArgumentParser(
        prog=program_name,
        description='Workflow simulator calibrator',
        epilog=epilog_string)

    try:

        parser.add_argument('-wd', '--workflow_dir', type=str, metavar="<workflow dir>", required=True,
                            help='Directory that contains all workflow instances')


        return vars(parser.parse_args()), parser, None

    except argparse.ArgumentError as error:
        return None, parser, error


def main():
    from sklearn.metrics import r2_score
    print(r2_score([1,3,3,3,3,6], [3,3,3,3,3,3]))

    # Parse command-line arguments
    args, parser, error = parse_command_line_arguments(sys.argv[0])
    if not args:
        sys.stderr.write(f"Error: {error}\n")
        parser.print_usage()
        sys.exit(1)

    # Build lists of workflows
    search_string = f"{args['workflow_dir']}/" \
                    f"*-" \
                    f"*-" \
                    f"*-" \
                    f"*-" \
                    f"*-" \
                    f"*-" \
                    f"*-*.json"
    workflows = glob.glob(search_string)

    if len(workflows) == 0:
        sys.stdout.write(f"No workflows found ({search_string})\n")
        sys.exit(1)
    else:
        sys.stderr.write(f"Found {len(workflows)} to process...\n")

    # Build list of workflow names and architectures
    workflow_names = set({})
    architectures = set({})
    for workflow in workflows:
        tokens = workflow.split('/')[-1].split("-")
        workflow_names.add(tokens[0])
        architectures.add(tokens[5])
    workflow_names = sorted(list(workflow_names))
    architectures = sorted(list(architectures))


    for workflow_name in workflow_names:
        for architecture in architectures:
            print(f"{workflow_name} on {architecture}:")
            search_string = f"{args['workflow_dir']}/" \
                            f"{workflow_name}-" \
                            f"*-" \
                            f"*-" \
                            f"*-" \
                            f"*-" \
                            f"{architecture}-" \
                            f"*-*.json"
            workflows = glob.glob(search_string)
            num_tasks_values = set({})
            cpu_values = set({})
            data_values = set({})
            num_nodes_values = set({})
            for workflow in workflows:
                tokens = workflow.split('/')[-1].split("-")
                num_tasks_values.add(int(tokens[1]))
                cpu_values.add(int(tokens[2]))
                data_values.add(int(tokens[4]))
                num_nodes_values.add(int(tokens[6]))
            num_tasks_values = sorted(list(num_tasks_values))
            cpu_values = sorted(list(cpu_values))
            data_values = sorted(list(data_values))
            num_nodes_values = sorted(list(num_nodes_values))

            coeffs_of_variance = []
            for num_tasks in num_tasks_values:
                for cpu in cpu_values:
                    for data in data_values:
                        for num_nodes in num_nodes_values:
                            search_string = f"{args['workflow_dir']}/{workflow_name}-{num_tasks}-{cpu}-0.6-{data}-{architecture}-{num_nodes}-*"
                            workflows = glob.glob(search_string)
                            makespans = [get_makespan(workflow) for workflow in workflows]
                            if len(makespans) > 1:
                                coeff_of_variance = variation(makespans)
                                coeffs_of_variance.append(coeff_of_variance)

            if len(coeffs_of_variance) == 0:
                continue
            average_coeff_of_variance = sum(coeffs_of_variance) / len(coeffs_of_variance)
            print(f"  max coeff of variance={max(coeffs_of_variance)}")
            print(f"  ave coeff of variance={average_coeff_of_variance}")


if __name__ == "__main__":
    main()
