#!/usr/bin/env python3
import glob
import json
import os
from pathlib import Path
from typing import List
import argparse
import sys
import pickle

from Simulator import Simulator
from WorkflowSimulatorCalibrator import WorkflowSimulatorCalibrator

from sklearn.metrics import mean_squared_error as sklearn_mean_squared_error

import simcal as sc


class Scenario:
    def __init__(self, simulator, ground_truth, loss):
        self.simulator = simulator
        self.ground_truth = ground_truth
        self.loss_function = loss

    def __call__(self, calibration):
        res = []
        # Run simulator for all known ground truth points
        print(calibration)
        for x in self.ground_truth[0]:
            res.append(self.simulator((x, calibration)))
        return self.loss_function(res, self.ground_truth[1])


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
    parser.add_argument('-tl', '--time_limit', type=str, metavar="<number of second>", nargs='?',
                        default=60, help='A training time limit, in seconds')
    parser.add_argument('-th', '--num_threads', type=str, metavar="<number of threads>", nargs='?',
                        default=1, help='A number of threads to use for training')

    args = vars(parser.parse_args())

    # Sanity check command-line arguments
    if args["train"] and args["input_calibration"]:
        sys.stderr.write("Error: Cannot specify any --train argument if a --input_calibration argument is present\n")
        sys.exit(1)

    if args["input_calibration"] is None and args["train"] is None:
        sys.stderr.write("Error: There should be one or more --train arguments or one --input_calibration argument\n")
        sys.exit(1)

    if args["train"] is None and args["output_calibration"]:
        sys.stderr.write("Error: Specifying a --output_calibration argument is only allowed if at least "
                         "one --train argument is present\n")
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


def obtain_calibration(args: dict[str, str | List[str]]) -> dict[str, sc.parameters.Value]:
    if args["input_calibration"]:
        sys.stderr.write(f"Loading calibration from file...\n")
        with open(args["input_calibration"], 'rb') as file:
            pickled_calibration = pickle.load(file)
            calibration = pickled_calibration["calibration"]

            # Consistency checking
            if pickled_calibration["compute_service_scheme"] != args["compute_service_scheme"]:
                sys.stderr.write(f"Loading calibration's compute service scheme ("
                                 f"{pickled_calibration['compute_service_scheme']}) "
                                 f"inconsistent with command-line arguments ({args['compute_service_scheme']})")
            if pickled_calibration["storage_service_scheme"] != args["storage_service_scheme"]:
                sys.stderr.write(f"Loading calibration's storage service scheme ("
                                 f"{pickled_calibration['storage_service_scheme']}) "
                                 f"inconsistent with command-line arguments ({args['storage_service_scheme']})")
            if pickled_calibration["network_topology_scheme"] != args["network_topology_scheme"]:
                sys.stderr.write(f"Loading calibration's' network topology scheme ("
                                 f"{pickled_calibration['network_topology_scheme']}) "
                                 f"inconsistent with command-line arguments ({args['network_topology_scheme']})")

            sys.stderr.write(f"  calibration loss: {pickled_calibration['loss']}\n")

    else:
        sys.stderr.write(f"Computing calibration using {len(args['train'])} workflows...\n")
        calibrator = WorkflowSimulatorCalibrator(args["train"],
                                                 Simulator(),
                                                 args["compute_service_scheme"],
                                                 args["storage_service_scheme"],
                                                 args["network_topology_scheme"],
                                                 sklearn_mean_squared_error)
        calibration, loss = calibrator.compute_calibration(float(args["time_limit"]),
                                                           int(args["num_threads"]))
        sys.stderr.write(f"  calibration loss: {loss}\n")

        # Save the calibration if need be
        if args["output_calibration"]:
            to_pickle = {"calibration": calibration,
                         "loss": loss,
                         "compute_service_scheme": args["compute_service_scheme"],
                         "storage_service_scheme": args["storage_service_scheme"],
                         "network_topology_scheme": args["network_topology_scheme"]}
            # Save it
            with open(args["output_calibration"], 'wb') as f:
                pickle.dump(to_pickle, f)
            sys.stderr.write(f"Saved computed calibration to '{args['output_calibration']}'\n")

    return calibration


def evaluate_calibration(args: dict[str, str | List[str]], calibration: dict[str, sc.parameters.Value]) -> float:
    simulator = Simulator()
    results = []
    sys.stderr.write(f"Evaluating calibration on {len(args['eval'])} workflows...\n")
    for workflow in args["eval"]:
        res = simulator((workflow, calibration))
        results.append(res)
    simulated_makespans, real_makespans = zip(*results)
    return sklearn_mean_squared_error(simulated_makespans, real_makespans)


def main():

    # Parse command-line arguments
    args = parse_command_line_arguments(sys.argv[0])

    # Obtain the calibration
    calibration = obtain_calibration(args)

    # Perform the evaluation if needed
    if args["eval"]:
        evaluation_loss = evaluate_calibration(args, calibration)
        sys.stderr.write(f"  evaluation loss: {evaluation_loss}\n")


if __name__ == "__main__":
    main()
