#!/usr/bin/env python3
import argparse

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
        parser.add_argument('-wn', '--workflow_name', type=str, metavar="<workflow names>", required=True,
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
                            metavar="[mean_square_error, relative_average_error]",
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



    # Pickle results
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

    # to_pickle = {"workflow_name": args['workflow_name'],
    #              "architecture": args['architecture'],
    #              "compute_service_scheme": args['compute_service_scheme'],
    #              "storage_service_scheme": args['storage_service_scheme'],
    #              "network_topology_scheme": args['network_topology_scheme'],
    #              "algorithm": args['algorithm'],
    #              "time_limit": args['time_limit'],
    #              "num_threads": args['num_threads'],
    #              "computer_name": args['computer_name'],
    #              "results": experiments_to_runs
    #              }

    # Pickle it
    # with open(pickle_file_name, 'wb') as f:
    #     pickle.dump(to_pickle, f)
    # sys.stderr.write(f"Pickled to ./{pickle_file_name}\n")
    #

if __name__ == "__main__":
    main()
