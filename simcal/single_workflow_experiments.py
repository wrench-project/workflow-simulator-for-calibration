#!/usr/bin/env python3
import os
import glob
import argparse

import simcal

from Util import *


class WorkflowSetSpec:
    def __init__(self, workflow_dir: str, workflow_name: str, architecture: str,
                 num_task_values: List[int], data_values: List[int], cpu_values: List[int],
                 num_nodes_values: List[int]):
        self.workflow_dir = workflow_dir
        self.workflow_name = workflow_name
        self.architecture = architecture
        self.num_task_values = num_task_values
        self.data_values = data_values
        self.cpu_values = cpu_values
        self.num_nodes_values = num_nodes_values

        self.workflows = []
        for num_task_value in num_task_values:
            for data_value in data_values:
                for cpu_value in cpu_values:
                    for num_nodes_value in num_nodes_values:
                        search_string = f"{self.workflow_dir}/{self.workflow_name}-"
                        search_string += str(num_task_value) + "-"
                        search_string += str(cpu_value) + "-"
                        search_string += "*-"
                        search_string += str(data_value) + "-"
                        search_string += f"{self.architecture}-"
                        search_string += str(num_nodes_value) + "-"
                        search_string += "*.json"
                        self.workflows += glob.glob(search_string)

        self.workflows = [os.path.abspath(x) for x in self.workflows]

    def get_workflow_set(self):
        return self.workflows

    def is_empty(self):
        return len(self.workflows) == 0

    def __repr__(self):
        return f"#tasks: {self.num_task_values}, #nodes: {self.num_nodes_values}, " \
               f"data: {self.data_values}, cpu: {self.cpu_values}"

    def __eq__(self, other: object):
        if not isinstance(other, WorkflowSetSpec):
            return NotImplemented
        to_return = (self.workflow_dir == other.workflow_dir) and \
                    (self.workflow_name == other.workflow_name) and \
                    (self.architecture == other.architecture) and \
                    (self.num_task_values == other.num_task_values) and \
                    (self.data_values == self.data_values) and \
                    (self.cpu_values == self.cpu_values) and \
                    (self.num_nodes_values == other.num_nodes_values)
        return to_return


class Experiment:
    def __init__(self,
                 training_set_spec: WorkflowSetSpec,
                 evaluation_set_specs: List[WorkflowSetSpec]):

        self.training_set_spec = training_set_spec
        # Remove duplicates from the evaluation set specs
        no_dup_evaluation_set_specs = []
        for evaluation_set in evaluation_set_specs:
            if evaluation_set not in no_dup_evaluation_set_specs:
                no_dup_evaluation_set_specs.append(evaluation_set)
        self.evaluation_set_specs = no_dup_evaluation_set_specs

        self.calibration: dict[str, sc.parameters.Value] | None = None
        self.calibration_loss: float | None = None
        self.evaluation_loss: float | None = None

    def __eq__(self, other: object):
        if not isinstance(other, Experiment):
            return NotImplemented
        return (self.training_set_spec == other.training_set_spec) and \
               (self.evaluation_set_specs == other.evaluation_set_specs)

    def __repr__(self):
        eval_str = ""
        for eval_set in self.evaluation_set_specs:
            eval_str += f"  Evaluation: {eval_set}\n"
        return f"Training: {self.training_set_spec}\n{eval_str}"

    def __str__(self):
        return self.__repr__()


class ExperimentSet:
    def __init__(self, simulator: Simulator, algorithm: str, loss_function: str, time_limit: float, num_threads: int,
                 compute_service_scheme: str, storage_service_scheme: str, network_topology_scheme: str):
        self.simulator = simulator
        self.algorithm = algorithm
        self.loss_function = loss_function
        self.time_limit = time_limit
        self.num_threads = num_threads
        self.experiments: List[Experiment] = []
        self.compute_service_scheme = compute_service_scheme
        self.storage_service_scheme = storage_service_scheme
        self.network_topology_scheme = network_topology_scheme

    def add_experiment(self, training_set_spec: WorkflowSetSpec, evaluation_set_specs: List[WorkflowSetSpec]):
        if training_set_spec.is_empty():
            # Perhaps print a message?
            return
        non_empty_evaluation_set_specs = []
        for evaluation_set_spec in evaluation_set_specs:
            if not evaluation_set_spec.is_empty():
                non_empty_evaluation_set_specs.append(evaluation_set_spec)
        if len(non_empty_evaluation_set_specs) == 0:
            # Perhaps print a message?
            return

        xp = Experiment(training_set_spec, evaluation_set_specs)
        if xp not in self.experiments:
            self.experiments.append(xp)

    def compute_all_calibrations(self):
        # Make a set of unique training_set_specs
        training_set_specs = []

        for xp in self.experiments:
            if xp.training_set_spec not in training_set_specs:
                training_set_specs.append(xp.training_set_spec)

        # For each unique training_set_spec: compute the calibration and store it in the experiments
        count = 1
        for training_set_spec in training_set_specs:
            sys.stderr.write(f"  Computing calibration #{count}/{len(training_set_specs)}  "
                             f" ({self.algorithm}, {self.time_limit} sec, {self.num_threads} threads)...\n")

            count += 1
            calibration, calibration_loss = compute_calibration(
                training_set_spec.get_workflow_set(),
                self.algorithm,
                self.simulator,
                self.compute_service_scheme,
                self.storage_service_scheme,
                self.network_topology_scheme,
                self.loss_function,
                self.time_limit,
                self.num_threads)
            # update all relevant experiments (inefficient, but shouldn't be too many xps)
            for xp in self.experiments:
                if xp.training_set_spec == training_set_spec:
                    xp.calibration = calibration
                    xp.calibration_loss = calibration_loss

    def compute_all_evaluations(self):
        # Here we're ok doing possible redundant work since evaluation is cheap
        count = 1
        for xp in self.experiments:
            sys.stderr.write(f"Performing evaluation #{count} / {len(self.experiments)}...\n")
            count += 1
            sys.stderr.write(f"  Evaluating a calibration...\n")
            for evaluation_set_spec in xp.evaluation_set_specs:
                xp.evaluation_loss = evaluate_calibration(
                    evaluation_set_spec.get_workflow_set(),
                    self.simulator,
                    xp.calibration,
                    self.loss_function)

    def run(self):
        # Computing all needed calibrations (which can be redundant across experiments, so let's not be stupid)
        self.compute_all_calibrations()
        self.compute_all_evaluations()

    def __repr__(self):
        set_str = ""
        for xp in self.experiments:
            set_str += f"{xp}\n"
        return set_str

    def __len__(self):
        return len(self.experiments)

    def __getitem__(self, item):
        return self.experiments[item]  # delegate to li.__getitem__


def parse_command_line_arguments(program_name: str):
    epilog_string = ""

    parser = argparse.ArgumentParser(
        prog=program_name,
        description='Workflow simulator calibrator',
        epilog=epilog_string)

    try:

        parser.add_argument('-wd', '--workflow_dir', type=str, metavar="<workflow dir>", required=True,
                            help='Directory that contains all workflow instances')

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
        sys.stderr.write(f"ERROR: {error}\n")
        parser.print_usage()
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

    workflows = glob.glob(search_string)
    # workflows = [os.path.abspath(x) for x in workflows]  # Make all path absolute
    if len(workflows) == 0:
        sys.stdout.write(f"No workflow found ({search_string})\n")
        sys.exit(1)

    # Build lists of the characteristics for which we have data44
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

    experiments_to_runs = ExperimentSet(Simulator(),
                                        args["algorithm"],
                                        args["loss_function"],
                                        args["time_limit"],
                                        args["num_threads"],
                                        args["compute_service_scheme"],
                                        args["storage_service_scheme"],
                                        args["network_topology_scheme"])

    sys.stderr.write("Creating experiments (glob.glob() takes a while)...\n")
    # Num task variation experiments
    for i in range(1, len(num_tasks_values)):
        for num_nodes in num_nodes_values:
            experiments_to_runs.add_experiment(
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

    # Num nodes variation experiments
    for i in range(1, len(num_nodes_values)):
        for num_tasks in num_tasks_values:
            experiments_to_runs.add_experiment(
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

    # "Bogus" Experiments to show that data and CPU should be diverse
    for i in range(1, len(num_tasks_values)):
        for num_nodes in [num_nodes_values[-1]]:
            experiments_to_runs.add_experiment(
                WorkflowSetSpec(args["workflow_dir"],
                                args["workflow_name"],
                                args["architecture"],
                                num_tasks_values[0:i], data_values[-1:], cpu_values[-1:], [num_nodes]),
                [
                    WorkflowSetSpec(args["workflow_dir"],
                                    args["workflow_name"],
                                    args["architecture"],
                                    num_tasks_values[-1:], data_values[-1:], cpu_values[-1:], [num_nodes])
                ])

    for i in range(1, len(num_nodes_values)):
        for num_tasks in [num_tasks_values[-1]]:
            experiments_to_runs.add_experiment(
                WorkflowSetSpec(args["workflow_dir"],
                                args["workflow_name"],
                                args["architecture"],
                                [num_tasks], data_values[-1:], cpu_values[-1:], num_nodes_values[0:i]),
                [
                    WorkflowSetSpec(args["workflow_dir"],
                                    args["workflow_name"],
                                    args["architecture"],
                                    [num_tasks], data_values[-1:], cpu_values[-1:], num_nodes_values[-1:])
                ])


    # print(experiments_to_runs)
    sys.stderr.write(f"Running {len(experiments_to_runs)} experiments...\n")

    # Run experiments (which fills in all losses and calibrations)
    experiments_to_runs.run()

    # Pickle results


if __name__ == "__main__":
    main()
