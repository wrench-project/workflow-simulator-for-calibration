#!/usr/bin/env python3
import glob
import json
import os
from pathlib import Path
from typing import List
import argparse
import sys

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

    parser.add_argument('-t', '--train', type=str, metavar="space-separated list of files", nargs='*',
                        help='WfInstances to train on')
    parser.add_argument('-e', '--eval', type=str, metavar="space-separated list of files", nargs='*',
                        help='WfInstances to evaluate on')
    parser.add_argument('-c', '--input_calibration', type=str, metavar="<path to JSON file>", nargs='?', default=None,
                        help='File that contains the calibration to use for the evaluation')
    parser.add_argument('-o', '--output_calibration', type=str, metavar="<path to JSON file>", nargs='?', default=None,
                        help='File to which the computed calibration should be written')
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

    return args


def main():

    # Parse command-line arguments
    args = parse_command_line_arguments(sys.argv[0])
    # print(args)

    # Instantiate the simulator
    simulator = Simulator()

    # Obtain the calibration
    calibration = None
    if args["input_calibration"]:
        with open(args["input_calibration"]) as json_file:
            calibration = json.loads(json_file.read())
            json_file.close()

    else:
        args["train"] = [os.path.abspath(x) for x in args["train"]]
        calibrator = WorkflowSimulatorCalibrator(args["train"],
                                                 simulator,
                                                 args["compute_service_scheme"],
                                                 args["storage_service_scheme"],
                                                 args["network_topology_scheme"],
                                                 sklearn_mean_squared_error)
        calibration, loss = calibrator.compute_calibration()
        calibration["loss"] = loss
        print(calibration)

    # Save the calibration if need be
    # TODO

    # Perform the evaluation if needed
    # TODO


if __name__ == "__main__":
    main()
