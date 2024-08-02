#!/usr/bin/env python3
import argparse
import time
from glob import glob
from datetime import timedelta

from Util import *


def parse_command_line_arguments(program_name: str):
    epilog_string = ""

    parser = argparse.ArgumentParser(
        prog=program_name,
        description='Workflow simulator calibrator',
        epilog=epilog_string)

    try:

        parser.add_argument('-wd', '--workflow_dir', type=str, metavar="<workflow dir>", required=True,
                            help='Directory that contains all workflow instances')
        parser.add_argument('-cn', '--computer_name', type=str, metavar="<computer name>", required=True,
                            help='Name of this computer to add to the pickled file name')
        parser.add_argument('-wn', '--workflow_name', type=str, metavar="<workflow name>", required=True,
                            help='Name of the workflow to run the calibration/validation on')
        parser.add_argument('-ar', '--architecture', type=str,
                            metavar="[haswell|skylake|cascadelake]",
                            choices=['haswell', 'skylake', 'cascadelake'], required=True,
                            help='The computer architecture')
        parser.add_argument('-al', '--algorithm', type=str,
                            metavar="[grid|random|gradient]",
                            choices=['grid', 'random', 'gradient'], required=True,
                            help='The calibration algorithm')
        parser.add_argument('-tl', '--time_limit', type=int, metavar="<number of second>", required=True,
                            help='A training time limit, in seconds')
        parser.add_argument('-th', '--num_threads', type=int, metavar="<number of threads (default=1)>", nargs='?',
                            default=1, help='A number of threads to use for training')
        parser.add_argument('-n', '--estimate_run_time_only', action="store_true",
                            help='A number of threads to use for training')
        parser.add_argument('-lf', '--loss_function', type=str,
                            metavar="mean_square_error, relative_average_error",
                            choices=['mean_square_error', 'relative_average_error'], nargs='?',
                            default="relative_average_error",
                            help='The loss function to evaluate a calibration')
        parser.add_argument('-cs', '--compute_service_scheme', type=str,
                            metavar="[all_bare_metal|htcondor_bare_metal]",
                            choices=['all_bare_metal', 'htcondor_bare_metal'], required=True,
                            help='The compute service scheme used by the simulator')
        parser.add_argument('-ss', '--storage_service_scheme', type=str,
                            metavar="[submit_only|submit_and_compute_hosts]",
                            choices=['submit_only', 'submit_and_compute_hosts'], required=True,
                            help='The storage service scheme used by the simulator')
        parser.add_argument('-ns', '--network_topology_scheme', type=str,
                            metavar="[one_link|one_and_then_many_links|many_links]",
                            choices=['one_link', 'one_and_then_many_links', 'many_links'], required=True,
                            help='The network topology scheme used by the simulator')

        return vars(parser.parse_args()), parser, None

    except argparse.ArgumentError as error:
        return None, parser, error


def main():
    # Parse command-line arguments
    args, parser, error = parse_command_line_arguments(sys.argv[0])
    if not args:
        sys.stderr.write(f"Error: {error}\n")
        parser.print_usage()
        sys.exit(1)

    # Pickle results filename
    pickle_file_name = f"pickled-one_workflow_experiments-" \
                       f"{args['workflow_name']}-" \
                       f"{args['architecture']}-" \
                       f"{args['compute_service_scheme']}-" \
                       f"{args['storage_service_scheme']}-" \
                       f"{args['network_topology_scheme']}-" \
                       f"{args['algorithm']}-" \
                       f"{args['time_limit']}-" \
                       f"{args['num_threads']}-" \
                       f"{args['computer_name']}.pickled"

    # If the pickled file already exists, then print a warning and move on
    if os.path.isfile(pickle_file_name):
        sys.stderr.write(f"There is already a pickled file '{pickle_file_name}'... Not doing anything!\n")
        sys.exit(1)

    # Build list of workflows
    search_string = f"{args['workflow_dir']}/" \
                    f"{args['workflow_name']}-" \
                    f"*-" \
                    f"*-" \
                    f"*-" \
                    f"*-" \
                    f"{args['architecture']}-" \
                    f"*-*.json"

    workflows = glob(search_string)
    # workflows = [os.path.abspath(x) for x in workflows]  # Make all path absolute
    if len(workflows) == 0:
        sys.stdout.write(f"No workflow found ({search_string})\n")
        sys.exit(1)

    # Build lists of the characteristics for which we have data
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

    sys.stderr.write(f"Found {len(workflows)} {args['workflow_name']} workflows to work with: \n")
    sys.stderr.write(f"  #tasks:         {num_tasks_values}\n")
    sys.stderr.write(f"  cpu work:       {cpu_values}\n")
    sys.stderr.write(f"  data footprint: {data_values}\n")
    sys.stderr.write(f"  #compute nodes: {num_nodes_values}\n\n")

    simulator = Simulator(args["compute_service_scheme"],
                          args["storage_service_scheme"],
                          args["network_topology_scheme"])

    experiment_set = ExperimentSet(simulator,
                                   args["algorithm"],
                                   args["loss_function"],
                                   args["time_limit"],
                                   args["num_threads"])

    sys.stderr.write("Creating experiments")
    # Num task variation experiments
    for i in range(1, len(num_tasks_values)):
        for num_nodes in num_nodes_values:
            experiment_set.add_experiment(
                WorkflowSetSpec(args["workflow_dir"],
                                args["workflow_name"],
                                args["architecture"],
                                num_tasks_values[0:i], data_values, cpu_values, [num_nodes]),
                [
                    WorkflowSetSpec(args["workflow_dir"],
                                    args["workflow_name"],
                                    args["architecture"],
                                    num_tasks_values[i:], data_values, cpu_values, [num_nodes]),
                    WorkflowSetSpec(args["workflow_dir"],
                                    args["workflow_name"],
                                    args["architecture"],
                                    [num_tasks_values[-1]], data_values, cpu_values, [num_nodes]),
                ])
        # Overfitting "control" experiment
        experiment_set.add_experiment(
            WorkflowSetSpec(args["workflow_dir"],
                            args["workflow_name"],
                            args["architecture"],
                            [num_tasks_values[i]], data_values, cpu_values, num_nodes_values),
            [
                WorkflowSetSpec(args["workflow_dir"],
                                args["workflow_name"],
                                args["architecture"],
                                [num_tasks_values[i]], data_values, cpu_values, num_nodes_values),
            ])

    # Num nodes variation experiments
    for i in range(1, len(num_nodes_values)):
        for num_tasks in num_tasks_values:
            experiment_set.add_experiment(
                WorkflowSetSpec(args["workflow_dir"],
                                args["workflow_name"],
                                args["architecture"],
                                [num_tasks], data_values, cpu_values, num_nodes_values[0:i]),
                [
                    WorkflowSetSpec(args["workflow_dir"],
                                    args["workflow_name"],
                                    args["architecture"],
                                    [num_tasks], data_values, cpu_values, num_nodes_values[i:]),
                    WorkflowSetSpec(args["workflow_dir"],
                                    args["workflow_name"],
                                    args["architecture"],
                                    [num_tasks], data_values, cpu_values, [num_nodes_values[-1]]),
                ])
        # Overfitting "control" experiment
        experiment_set.add_experiment(
            WorkflowSetSpec(args["workflow_dir"],
                            args["workflow_name"],
                            args["architecture"],
                            num_tasks_values, data_values, cpu_values, [num_nodes_values[i]]),
            [
                WorkflowSetSpec(args["workflow_dir"],
                                args["workflow_name"],
                                args["architecture"],
                                num_tasks_values, data_values, cpu_values, [num_nodes_values[i]]),
            ])

    # "Bogus" Experiments to show that data and CPU should be diverse
    for i in range(1, len(num_tasks_values)):
        for num_nodes in [num_nodes_values[-1]]:
            added = False
            for data_value in data_values:
                for cpu_value in cpu_values:
                    added = experiment_set.add_experiment(
                        WorkflowSetSpec(args["workflow_dir"],
                                        args["workflow_name"],
                                        args["architecture"],
                                        num_tasks_values[0:i], [data_value], [cpu_value], [num_nodes]),
                        [
                            WorkflowSetSpec(args["workflow_dir"],
                                            args["workflow_name"],
                                            args["architecture"],
                                            num_tasks_values[-1:], data_values, cpu_values, [num_nodes])
                        ])
                    if added:
                        break
                if added:
                    break

    for i in range(1, len(num_nodes_values)):
        for num_tasks in [num_tasks_values[-1]]:
            added = False
            for data_value in data_values:
                for cpu_value in cpu_values:
                    added = experiment_set.add_experiment(
                        WorkflowSetSpec(args["workflow_dir"],
                                        args["workflow_name"],
                                        args["architecture"],
                                        [num_tasks], [data_value], [cpu_value], num_nodes_values[0:i]),
                        [
                            WorkflowSetSpec(args["workflow_dir"],
                                            args["workflow_name"],
                                            args["architecture"],
                                            [num_tasks], data_values, cpu_values, num_nodes_values[-1:])
                        ])
                    if added:
                        break
                if added:
                    break

    sys.stderr.write(f"\nCreated {len(experiment_set)} experiments...\n")

    time_estimate_str = timedelta(seconds=experiment_set.estimate_run_time())

    if args['estimate_run_time_only']:
        sys.stderr.write(f"Experiments should take about {time_estimate_str}\n")
        sys.exit(0)

    sys.stderr.write(f"Running experiments (should take about {time_estimate_str})\n")
    # try:
    start = time.perf_counter()
    experiment_set.run()
    elapsed = int(time.perf_counter() - start)
    sys.stderr.write(f"Actually ran in {timedelta(seconds=elapsed)}\n")
    # except Exception as error:
    #    sys.stderr.write(str(type(error)))
    #    sys.stderr.write(f"Error while running experiments: {error}\n")
    #    sys.exit(1)
    # dont catch print exit errors.  Just let the error throw its self and python will give a much better print then still exit

    # Pickle it
    with open(pickle_file_name, 'wb') as f:
        pickle.dump(experiment_set, f)
    sys.stderr.write(f"Pickled to ./{pickle_file_name}\n")


if __name__ == "__main__":
    main()
