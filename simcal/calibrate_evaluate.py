#!/usr/bin/env python3
import os
import argparse

from Util import *


def parse_command_line_arguments(program_name: str):
    epilog_string = f"""Example:
python3 {program_name} --train workflow-*-*-10*.json  other_workflow.json 
        --eval workflow-*-*-20*.json --output_calibration /tmp/cal.json 
        --compute_service_scheme all_bare_metal 
        --storage_service_scheme submit_only 
        --network_topology_scheme one_and_then_many_links  
"""

    parser = argparse.ArgumentParser(
        prog=program_name,
        description='Workflow simulator calibrator',
        epilog=epilog_string)

    parser.add_argument('-t', '--train', type=str, metavar="<space-separated list of files>", nargs='*',
                        help='WfInstances to train on')
    parser.add_argument('-a', '--algorithm', type=str,
                        metavar="[grid|random|gradient]",
                        choices=['grid', 'random', 'gradient'], required=True,
                        help='The calibration algorithm')
    parser.add_argument('-e', '--eval', type=str, metavar="<space-separated list of files>", nargs='*',
                        help='WfInstances to evaluate on')
    parser.add_argument('-ic', '--input_calibration', type=str, metavar="<path to file>", nargs='?', default=None,
                        help='File that contains the calibration to use for the evaluation')
    parser.add_argument('-oc', '--output_calibration', type=str, metavar="<path to file>", nargs='?', default=None,
                        help='File to which the computed calibration should be saved')
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
    parser.add_argument('-tl', '--time_limit', type=str, metavar="<number of second>", required=True,
                        help='A training time limit, in seconds')
    parser.add_argument('-th', '--num_threads', type=str, metavar="<number of threads (default=1)>", nargs='?',
                        default=1, help='A number of threads to use for training')
    parser.add_argument('-lf', '--loss_function', type=str,
                        metavar="[mean_square_error]",
                        choices=['mean_square_error'], required=True,
                        help='The loss function to evaluate a calibration')

    args = vars(parser.parse_args())

    # Sanity check command-line arguments
    if args["train"] and args["input_calibration"]:
        sys.stderr.write("Error: Cannot specify any --train argument if a --input_calibration argument is present\n")
        sys.exit(1)

    if args["input_calibration"] is None and args["train"] is None:
        sys.stderr.write("Error: There should be one --train arguments or one --input_calibration argument\n")
        sys.exit(1)

    # Clean up file paths to be absolute, just in case
    if args["train"]:
        args["train"] = [os.path.abspath(x) for x in args["train"]]
    if args["eval"]:
        args["eval"] = [os.path.abspath(x) for x in args["eval"]]
    if args["input_calibration"]:
        args["input_calibration"] = os.path.abspath(args["input_calibration"])
    if args["output_calibration"]:
        args["output_calibration"] = os.path.abspath(args["output_calibration"])

    return args


def main():
    # Parse command-line arguments
    args = parse_command_line_arguments(sys.argv[0])

    # Instantiate a simulator object
    simulator = Simulator()

    # Obtain the calibration
    if args["input_calibration"]:
        sys.stderr.write(f"Loading calibration from '{args['input_calibration']}...\n")
        calibration, loss = load_pickled_calibration(args["input_calibration"],
                                                     args["compute_service_scheme"],
                                                     args["storage_service_scheme"],
                                                     args["network_topology_scheme"])
    else:
        sys.stderr.write(f"Computing calibration using {len(args['train'])} workflows...\n")
        calibration, loss = compute_calibration(args["train"],
                                                args["algorithm"],
                                                simulator,
                                                args["compute_service_scheme"],
                                                args["storage_service_scheme"],
                                                args["network_topology_scheme"],
                                                args["loss_function"],
                                                float(args["time_limit"]),
                                                int(args["num_threads"]))

    sys.stderr.write(f"  calibration loss: {loss}\n")

    if args["output_calibration"]:
        save_pickled_calibration(args["output_calibration"], calibration, loss,
                                 args["compute_service_scheme"],
                                 args["storage_service_scheme"],
                                 args["network_topology_scheme"])
        sys.stderr.write(f"Saved calibration to '{args['output_calibration']}'.\n")

    # Perform the evaluation if needed
    if args["eval"]:
        sys.stderr.write(f"Evaluating calibration on {len(args['eval'])} workflows...\n")
        evaluation_loss = evaluate_calibration(args["eval"],
                                               simulator,
                                               calibration,
                                               args["loss_function"])
        sys.stderr.write(f"  evaluation loss: {evaluation_loss}\n")


if __name__ == "__main__":
    main()
