#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (c) 2022. Loïc Pottier <pottier1@llnl.gov>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from __future__ import annotations
import sys
from os import mkdir, remove, environ, getcwd

if sys.version_info[0] != 3 or sys.version_info[1] >= 10:
    print(
        f"ERROR: This script requires Python >=3.7 <3.10. \
        You are using Python {sys.version_info[0]}.{sys.version_info[1]}")
    sys.exit(-1)

# Mandatory to load the simulator if SimGrid and WRENCH shared lib
# are not located in /usr/local/lib
if sys.platform == "darwin":
    if "DYLD_LIBRARY_PATH" not in environ:
        environ["DYLD_LIBRARY_PATH"] = ""
    environ["DYLD_LIBRARY_PATH"] = environ["DYLD_LIBRARY_PATH"] +":" + environ["HOME"] + "/local/lib/"

import atexit
import time
import re
import json
import logging
import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt

from math import isnan
from psutil import cpu_count
from shutil import copyfile
from functools import reduce
from subprocess import run, CalledProcessError
from uuid import uuid4
from argparse import ArgumentParser
from warnings import filterwarnings
from typing import Dict, List, Any, Union, Type, Tuple

from deephyper.search.hps import CBO
from deephyper.evaluator.callback import Callback, LoggerCallback, SearchEarlyStopping
from deephyper.evaluator import Evaluator
from deephyper.problem import HpProblem
import ConfigSpace as cs
import ConfigSpace.hyperparameters as csh

JSON = Union[Dict[str, Any], List[Any], int, str, float, bool, Type[None]]
SCHEMES = {"error": "error_computation_scheme",
           "compute": "compute_service_scheme",
           "storage": "storage_service_scheme",
           "network": "network_topology_scheme"}

# Docker container ID as a global variable
docker_container_id = ""
SEED = 0
LOGGER_NAME = __name__

##########################   Logging   ################################

class CustomFormatter(logging.Formatter):

    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    green = "\x1b[32m"
    bold_green = "\x1b[1;32m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format = "[%(levelname)s(%(asctime)s)][%(filename)s:%(lineno)s/%(funcName)s] - %(message)s"

    FORMATS = {
        logging.DEBUG: grey + format + reset,
        logging.INFO: grey + format + reset,
        logging.WARNING: grey + format + reset,
        logging.ERROR: yellow + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt='%Y:%m:%d-%I:%M:%S')
        return formatter.format(record)

def configure_logger(name: str = LOGGER_NAME, level: int = logging.WARNING) -> logging.Logger:
    """Configure the logger."""
    logger = logging.getLogger(LOGGER_NAME)
    # create console handler and set level to debug
    ch = logging.StreamHandler()
    ch.setFormatter(CustomFormatter())
    logger.addHandler(ch)
    logger.setLevel(level)

    logging.basicConfig(
        level=level,
        handlers=[ch]
    )

    return logger

class MyLoggerCallback(Callback):
    """Print information when jobs are completed by the ``Evaluator``.

    An example usage can be:

    >>> evaluator.create(method="ray", method_kwargs={..., "callbacks": [LoggerCallback()]})
    """

    def __init__(self):
        self._best_objective = None
        self._n_done = 0

    def on_done(self, job):
        self._n_done += 1
        # Test if multi objectives are received
        if np.ndim(job.result) > 0:
            if np.isreal(job.result).all():
                if self._best_objective is None:
                    self._best_objective = np.sum(job.result)
                else:
                    self._best_objective = max(np.sum(job.result), self._best_objective)

                logging.warning(
                    f"[{self._n_done:05d}] -- best sum(objective): {self._best_objective:.5f} -- received sum(objective): {np.sum(job.result):.5f}"
                )
            elif np.any(type(res) is str and "F" == res[0] for res in job.result):
                logging.error(f"[{self._n_done:05d}] -- received failure: {job.result}")
        elif np.isreal(job.result):
            if self._best_objective is None:
                self._best_objective = job.result
            else:
                self._best_objective = max(job.result, self._best_objective)

            logging.warning(
                f"[{self._n_done:05d}] -- best objective: {self._best_objective:.5f} -- received objective: {job.result:.5f}"
            )
        elif type(job.result) is str and "F" == job.result[0]:
            logging.error(f"[{self._n_done:05d}] -- received failure: {job.result}")


#######################################################################

def create_docker_container(docker_image) -> str:
    """
    Create a Docker container to run the simulator.
    Returns the container ID.
    """
    logging.warning(f"Starting Docker container for image {docker_image}")
    cmd = "docker run -it -d -v " + getcwd() + ":/home/wrench " + docker_image
    docker = run(cmd.split(" "), capture_output=True, text=True, timeout=int(10))
    if docker.stdout == '':
        raise CalledProcessError(docker.returncode, docker.args)
    docker.check_returncode()
    global docker_container_id
    docker_container_id = docker.stdout.strip()
    logging.warning(f"Docker container started ({docker_container_id[0:11]})")
    return docker.stdout.strip()


def kill_docker_container(docker_container_id: str) -> str:
    """Kill a Docker container."""
    logging.warning(f"Waiting for Docker container to idle...")
    zero_count = 0
    while zero_count < 3:
        time.sleep(1)
        cmd = "docker container stats --no-stream " + docker_container_id
        docker = run(cmd.split(" "), capture_output=True, text=True, timeout=int(10))
        docker.check_returncode()
        second_line = docker.stdout.split('\n')[1].strip()
        cpu_load = float(re.split(' +', second_line)[2].split("%")[0])
        # print(cpu_load)
        if (cpu_load <= 0):
            zero_count += 1
    logging.warning(f"Killing Docker container ({docker_container_id[0:11]})...")
    cmd = "docker kill " + docker_container_id
    docker = run(cmd.split(" "), capture_output=True, text=True, timeout=int(10))
    docker.check_returncode()
    logging.warning("Docker container killed")
    time.sleep(1)
    cmd = "docker rm " + docker_container_id
    docker = run(cmd.split(" "), capture_output=True, text=True, timeout=int(10))
    docker.check_returncode()
    logging.warning("Docker container removed")


def set_nested(d: dict, path :str, value: str) -> None:
    """
    Helper function to create the right nested configuration (JSON)

    """
    def _get_nested_default(d: dict, path: str):
        return reduce(lambda d, k: d.setdefault(k, {}), path, d)

    _get_nested_default(d, path[:-1])[path[-1]] = value

# Should depend upon ConfigSpace from DeepHyper
class CalibrationConfiguration(object):
    """
    This class represents a configuration for a calibration.
    """
    def __init__(self, config: Path) -> None:

        self.logger = logging
        self.config: JSON = self._load_json(config)
        self.ranges = self.config["calibration_ranges"]

    def _load_json(self, path: Path) -> JSON:
        """Load the JSON file that define the experiments."""
        with open(path, 'r') as stream:
            return json.load(stream)

    def get_range(self, key: str, strict: bool = False):
        """ 
        Quickly find the range that matches.
        If strict is True we match exactly, otherwise
        we match if substring
        """
        def get_recursively(search_dict, field, strict):
            if isinstance(search_dict, dict):
                if field in search_dict:
                    return search_dict[field]
                if not strict:
                    potential_match = dict(filter(lambda item: field in item[0], search_dict.items()))
                    if potential_match != {}:
                        return potential_match
                for key in search_dict:
                    item = get_recursively(search_dict[key], field, strict)
                    if item is not None:
                        return item
        return get_recursively(self.ranges, field = key, strict = strict) 


class Calibrator(object):
    """
    This class defines a WRENCH simulation auto-calibrator

    :param config: Path for the configuration file (JSON)
    :type config: Path
    :param workflows: A list of workflows calibrate together, defaults to [None].
    If None, the workflow(s) found in the config file will be used.
    :type workflows: List[Path]
    :param random_search: Perform a random search instead of a Bayesian 
    optimization, defaults to [False]
    :type random_search: bool
    :param max_evals: Number of iterations performed, defaults to [100]
    :type max_evals: int
    :param cores: Number of workers used 
    (by default: all available = number of physical cores), defaults to [None]
    :type cores: int
    :param wrench_timeout: Seconds after which the simulator is killed 
    for each iteration (if None = infinite), defaults to [None]
    :type wrench_timeout: int
    :param deephyper_timeout: Seconds after which DeepHyper is killed 
    (if None = infinite), defaults to [None]
    :type deephyper_timeout: int
    :param consider_properties: Calibrate properties, defaults to [True]
    :type consider_properties: Path
    :param consider_payloads: Calibrate payloads, defaults to [True]
    :type consider_payloads: bool
    :param output_dir: Output directory for all the files, defaults to [None]
    :type output_dir: str
    :param early_stop: If None DeepHyper will perform all iterations, 
    otherwise DeepHyper will stop after X iterations that did not improve 
    the objective , defaults to [None]
    :type early_stop: int
    :param compute_service_scheme: Specify the compute_service_scheme to
    use, defaults to [None]
    :type compute_service_scheme: str
    :param storage_service_scheme: Specify the storage_service_scheme to
    use, defaults to [None]
    :type storage_service_scheme: str
    :param network_topology_scheme: Specify the network_topology_scheme to
    use, defaults to [None]
    :type network_topology_scheme: str
    :param use_docker: use Docker to run the simulator, defaults to [False]
    :type use_docker: bool
    :param docker_container_id: The Docker container ID if running with
    Docker, defaults to [None]
    :type docker_container_id: str
    :param logger: The logger, defaults to [None]
    :type logger: logging.Logger

    :returns: A calibrator object
    :rtype: Calibrator
    """

    def __init__(self,
                config: Path,
                workflows: List[Path] = None,
                random_search: bool = False,
                max_evals: int = 100,
                cores: int = None,
                wrench_timeout: int = None,
                deephyper_timeout: int = None,
                consider_properties: bool = True,
                consider_payloads: bool = True,
                output_dir: str = None,
                early_stop: int = None,
                compute_service_scheme: str = None,
                storage_service_scheme: str = None,
                network_topology_scheme: str = None,
                logger: logging.Logger = None) -> None:

        self.logger = logging
        self.random_search = random_search
        self.max_evals = max_evals
        self.wrench_timeout = wrench_timeout
        self.deephyper_timeout = deephyper_timeout
        self.output_dir = output_dir
        self.early_stop = early_stop
        self.compute_service_scheme = compute_service_scheme
        self.storage_service_scheme = storage_service_scheme
        self.network_topology_scheme = network_topology_scheme
        self.consider_payloads = consider_payloads
        self.consider_properties = consider_properties
        self.config_path = str(config)
        self.config: JSON = self._load_json(config)

        # Default seed is 0
        self.seed = int(self.config.get("seed")) if self.config.get("seed") else 0
        global SEED
        SEED = self.seed

        # global docker_container_id
        # self.docker_container_id = docker_container_id
        # self.use_docker = docker_container_id != ""

        # self.configspace = cs.ConfigurationSpace()
        # self.configspace.seed(SEED)
        self.problem = HpProblem()
        self.problem.space.seed(self.seed)

        # Contains all ranges for all properties/payloads used under the form:
        #   {'property1': {'min': 0, 'max': 6, 'scale': 'log', 'unit': 'ms'}}
        self.calibration_ranges = self.config["calibration_ranges"]

        if cores:
            self.num_cpus = cores
        else:
            self.num_cpus = min(self.max_evals, int(cpu_count(logical=False)))

        #Use sub-process as back-end, to use ThreadPool -> "thread" 
        self.backend = "process"
        # Number of jobs used to compute the surrogate model ( -1 means max possible)
        self.n_jobs = -1

        self.simulator = self.config["simulator"]

        self.logger.warning(f"Trying to run {self.simulator} --version...")
        simu_ok = self._test_simulator()

        if simu_ok[0]:
            self.logger.warning(f"Success")
        else:
            simu_name = self.config["simulator"]
            self.logger.error(f"Failed to run the simulator (make sure that the simulator '{simu_name}' exists and is "
                              f"in the $PATH or that Docker is running)")
            exit(1)

        self.simulator_config: JSON = self._load_json(self.config["config"])

        # we can override the workflow in the config with --workflow
        if workflows:
            self.workflows: List[Path] = [Path(wf) for wf in workflows]
        else:
            self.workflows: List[Path] = [Path(self.simulator_config["workflow"]["file"])]
        
        for wf in self.workflows:
            if Path.is_file(wf):
                self.logger.warning(f"Calibrating {wf}")
            else:
                self.logger.error(f"The file {wf} does not exist.")
                exit(1)

        if self.consider_properties:
            self.logger.warning(f"We are calibrating properties")
        if self.consider_payloads:
            self.logger.warning(f"We are calibrating payloads.")

        self.sampling = self.get_sampling_method(self.config)

        self.schemes: Dict = SCHEMES
        # Override the schemes for compute, storage and topology (if needed)
        if compute_service_scheme:
            scheme_name = self.schemes["compute"]
            self.simulator_config[scheme_name] = compute_service_scheme
        if storage_service_scheme:
            scheme_name = self.schemes["storage"]
            self.simulator_config[scheme_name] = storage_service_scheme
        if network_topology_scheme:
            scheme_name = self.schemes["network"]
            self.simulator_config[scheme_name] = network_topology_scheme

        self.df: pd.DataFrame = {}  # Result
        if self.output_dir:
            self.csv_output: Path = Path(self.output_dir)
        else:
            self.output_dir = '.'

        self.add_parameters()

        callbacks = [MyLoggerCallback()]
        # Stop after EARLY_STOP evaluations that did not improve the search
        if self.early_stop:
            callbacks.append(SearchEarlyStopping(patience=self.early_stop))

        # define the evaluator to distribute the computation
        self.evaluator = Evaluator.create(
            self.worker,
            method=self.backend,
            method_kwargs={
                "num_workers": self.num_cpus,
                "callbacks": callbacks
            },
        )

        self.logger.warning(f"Evaluator has {self.evaluator.num_workers} available workers")

        if self.random_search:
            # When surrogate_model=DUMMY it performs a Random Search
            self.search = CBO(
                problem=self.problem,
                evaluator=self.evaluator,
                random_state=self.seed,
                n_jobs=self.n_jobs,
                surrogate_model="DUMMY",
                log_dir=self.output_dir,
            )
        else:
            self.search = CBO(
                problem=self.problem,
                evaluator=self.evaluator,
                random_state=self.seed,
                n_jobs=self.n_jobs,
                surrogate_model="RF",
                log_dir=self.output_dir
            )

    def get_sampling_method(self, config: JSON) -> str:
        sampling = config["sampling"]
        self.logger.warning(f"Using sampling = {sampling}")
        return sampling

    def _load_json(self, path: Path) -> JSON:
        """Load the JSON file that define the experiments."""
        with open(path, 'r') as stream:
            return json.load(stream)

    def write_json(self, data: JSON, path: Path) -> None:
        """Write a dict in a JSON file."""
        with open(path, 'w') as f:
            json.dump(data, f, indent=4)
            f.write('\n')

    def _get_range(self, key: str, strict: bool = False):
        """ 
        Quickly find the range that matches.
        If strict is True we match exactly, otherwise
        we match if substring
        """
        def get_recursively(search_dict, field, strict):
            if isinstance(search_dict, dict):
                if field in search_dict:
                    return search_dict[field]
                if not strict:
                    potential_match = dict(filter(lambda item: field in item[0], search_dict.items()))
                    if potential_match != {}:
                        return potential_match
                for key in search_dict:
                    item = get_recursively(search_dict[key], field, strict)
                    if item is not None:
                        return item
        return get_recursively(self.config["calibration_ranges"], key, strict = strict) 


    @staticmethod
    def _verify_range(a: int, b: int, sampling: str = None) -> Tuple[int, int, str] | List[int]:
        """We must verify that if a == b. Constants parameters cannot add it as hyperparameters 
        to DeepHyper and must be treated as a list of one element
            - if a > b we must return (a, b, sampling)
            - if a == b, we return [a]
            - if a < b -> raise an error
        """
        if a < b:
            return (a, b, sampling)
        elif a == b:
            return [a]
        else:
            raise ValueError(f"invalid range {a} not < {b}")

    @staticmethod
    def _verify_range(a: int, b: int, sampling: str) -> Tuple[int, int, str] | List[int]:
        """We must verify that if a == b. Constants parameters cannot add it as hyperparameters 
        to DeepHyper and must be treated as a list of one element
            - if a > b we must return (a, b, sampling)
            - if a == b, we return [a]
            - if a < b -> raise an error
        """
        if a < b:
            return (a, b, sampling)
        elif a == b:
            return [a]
        else:
            raise ValueError(f"invalid range {a} not < {b}")

    def _add_parameter(self, name: str) -> None:
        """
        Function that add the right parameter with its range.
        """
        line = name.split("-")
        # Get the range defined in the config file
        ranges = self._get_range(line[-1], strict = True)
        if "payloads" in name or "Payload" in name:
            ranges = self._get_range("payloads", strict = True)
        if ranges:
            is_log = ranges["scale"] == "log2"
            sampling = "log-" + self.sampling if is_log else self.sampling
            # We allow infinite value for that parameter (must be supported by WRENCH)
            is_infinite = ranges.get("infinity_allowed")
            value = line[-1].split("::")[-1] # We split in case of properties
            if value == "BUFFER_SIZE" and is_infinite:
                if ranges["min"] == ranges["max"]:
                    raise ValueError(f"Infinite value for {value} is not allowed for ranges "
                        f"where min == max (here {ranges['max']})")
                # Model the concurrent access/buffer size with two variables:
                # - inf or not inf
                #   - if not inf we pick a discrete value between MIN and MAX
                buffer_size_categorical = csh.CategoricalHyperparameter(
                    "CAT_"+name, choices=["infinity", "finite"])
                buffer_size_discrete = csh.UniformIntegerHyperparameter(
                    name, lower=ranges["min"], upper=ranges["max"], log=is_log)
                self.problem.add_hyperparameter(buffer_size_categorical)
                self.problem.add_hyperparameter(buffer_size_discrete)
                # If we choose "finite" then we sample a discrete value for the buffer size
                self.problem.add_condition(cs.EqualsCondition(
                    buffer_size_discrete, buffer_size_categorical, "finite"))
            elif value == "MAX_NUM_CONCURRENT_DATA_CONNECTIONS" and is_infinite:
                if ranges["min"] == ranges["max"]:
                    raise ValueError(f"Infinite value for {value} is not allowed for ranges "
                        f"where min == max (here {ranges['max']})")
                conc_conn_categorical = csh.CategoricalHyperparameter(
                    "CAT_"+name, choices=["infinity", "finite"])
                conc_conn_discrete = csh.UniformIntegerHyperparameter(
                    name, lower=ranges["min"], upper=ranges["max"], log=is_log)
                self.problem.add_hyperparameter(conc_conn_categorical)
                self.problem.add_hyperparameter(conc_conn_discrete)
                self.problem.add_condition(
                    cs.EqualsCondition(conc_conn_discrete, conc_conn_categorical, "finite")
                )
            else:
                self.problem.add_hyperparameter(
                    Calibrator._verify_range(ranges["min"], ranges["max"], sampling), name
                )
            self.logger.warning(
                f'Added parameter {line[-1]} for '
                f'calibration (min={ranges["min"]}, '
                f'max={ranges["max"]}, '
                f'scale={ranges["scale"]}, '
                f'unit={ranges.get("unit")})'
            )
        else:
            self.logger.error(f"Did not find calibration ranges for {line[-1]}. Ignored.")

    def add_parameters(self):
        """
        In DeepHyper we can add only unique parameter, so we build a unique parameter
        name by containing the hierarchy. For example, we want to add num_cores as parameter:
            "compute_service_scheme_parameters": {
                "all_bare_metal": {
                    "submit_host": {
                        "num_cores": "16"
                    }
                }
            }
        Then, we will add it as "compute_service_scheme_parameters-all_bare_metal-submit_host-num_cores"
        """
        self.problem.add_hyperparameter([str(self.simulator)], "simulator")
        self.problem.add_hyperparameter([str(wf) for wf in self.workflows], "workflow")
        self.problem.add_hyperparameter([str(self.output_dir)], "output_dir")
        self.problem.add_hyperparameter([str(self.wrench_timeout)], "timeout")
        self.problem.add_hyperparameter([str(self.config_path)], "config_path")

        for scheme in self.schemes.values():
            self.problem.add_hyperparameter(
                [self.simulator_config[scheme]], scheme)

        self._add_parameter("reference_flops")
        self._add_parameter("scheduling_overhead")

        for _, name_scheme in self.schemes.items():
            cs_scheme = self.simulator_config[name_scheme]
            cs_parameter = name_scheme+"_parameters"

            for elem in self.simulator_config[cs_parameter][cs_scheme]:
                if isinstance(self.simulator_config[cs_parameter][cs_scheme][elem], dict):
                    for item in self.simulator_config[cs_parameter][cs_scheme][elem]:
                        name = cs_parameter+"-"+cs_scheme+"-"+elem+"-"+item
                        self._add_parameter(name)
                else:
                    name = cs_parameter+"-"+cs_scheme+"-"+elem
                    self._add_parameter(name)


    def _test_simulator(self, use_docker: bool = False) -> Tuple[bool, str]:
        """
        Test the simulator to make sure it exists and that's 
        a valid WRENCH simulator
        """
        global docker_container_id

        if docker_container_id != "":
            cmd = ["docker", "exec", docker_container_id, self.simulator, "--version"]
        else:
            cmd = [self.simulator, "--version"]
        try:
            test_simu = run(
                cmd, capture_output=True, text=True, check=True
            )
        except (CalledProcessError, FileNotFoundError) as e:
            return (False, e)
        else:
            return (True, test_simu.stdout)

    @staticmethod
    def get_real_values_with_unit(name: str, val: any, calib_conf: CalibrationConfiguration) -> str:
        line = name.split('-')        
        updated_val = val
        configure_logger()

        if "payloads" in name or "Payload" in name:
            ranges = calib_conf.get_range("payloads", strict = True)
        else:
            ranges = calib_conf.get_range(line[-1], strict = True)

        if ranges:
            key = line[-1].split("::")[-1]
            is_log = ranges["scale"] == "log2"
            unit = str(ranges.get("unit")) if ranges.get("unit") else ""
            if key == "BUFFER_SIZE":
                if isnan(val):
                    # Here nan means the value must be infinite 
                    # and WRENCH understands it as "infinity"
                    updated_val = "infinity"
                else:
                    if is_log:
                        updated_val = str(2**int(val)) + unit
                    else:
                        updated_val = str(int(val)) + unit
            elif key == "MAX_NUM_CONCURRENT_DATA_CONNECTIONS":
                if isnan(val):
                    updated_val = "infinity"
                else:
                    if is_log:
                        updated_val = str(2**int(val)) + unit
                    else:
                        updated_val = str(int(val)) + unit
            else:
                if is_log:
                    updated_val = str(2**int(val)) + unit
                else:
                    updated_val = str(int(val)) + unit
        else:
            logging.critical(f"Did not find calibration ranges for {line[-1]}. Ignored.")

        if updated_val == val:
            logging.error(f"Value {val} has not been updated and scaled.")

        return updated_val

    @staticmethod
    def create_wrench_configuration(config: Dict) -> Dict:
        """
        Create a platform file and a WRENCH configuration 
        based on what DeepHyper picked.
        """
        wrench_conf = {}
        param_names = [x+"_parameters" for x in SCHEMES.values()]
        calibration_config = CalibrationConfiguration(config["config_path"])

        wrench_conf["workflow"] = {}
        wrench_conf["workflow"]["file"] = config["workflow"]

        ranges = calibration_config.get_range("reference_flops")
        if ranges["scale"] == "log2":
            wrench_conf["workflow"]["reference_flops"] = str(2**int(config["reference_flops"]))
        else:
            wrench_conf["workflow"]["reference_flops"] = str(int(config["reference_flops"]))
        wrench_conf["workflow"]["reference_flops"] += ranges["unit"]

        ranges = calibration_config.get_range("scheduling_overhead")
        if ranges["scale"] == "log2":
            wrench_conf["scheduling_overhead"] = str(2**int(config["scheduling_overhead"]))
        else:
            wrench_conf["scheduling_overhead"] = str(int(config["scheduling_overhead"]))

        wrench_conf["scheduling_overhead"] += ranges["unit"]

        for val in SCHEMES.values():
            wrench_conf[val] = config[val]
            wrench_conf[val+"_parameters"] = {}
            wrench_conf[val+"_parameters"][config[val]] = {}

        for key, val in config.items():
            path = key.split('-')
            if path[0] in param_names:
                updated_val = Calibrator.get_real_values_with_unit(key, val, calibration_config)
                set_nested(wrench_conf, path, updated_val)

        return wrench_conf

    @staticmethod
    def worker(config: Dict) -> float:
        """
        Launch one instance of a simulator in one sub-process
        based on a given configuration/platform.
        """
        # We must use a global variable here to ensure the seed used by DeepHyper
        # when using Docker or not remain the same...
        global docker_container_id
        err = 0.0
        # TODO: Make sure the seed is set correctly and == self.seed
        global SEED
        config["seed"] = SEED

        configure_logger()

        config_path = Path(f"{config['output_dir']}/config-{config['job_id']}.json")
        wrench_conf: Dict = Calibrator.create_wrench_configuration(config)
        use_docker: bool = "docker_container_id" in config

        # We write the configuration we got from DeepHyper as a JSON file for the simulator
        with open(config_path, 'w') as temp_config:
            json.dump(wrench_conf, temp_config, indent=4)
            temp_config.write('\n')
        try:
            if use_docker:
                cmd = ["docker", "exec", docker_container_id, config["simulator"], str(config_path)]
            else:
                cmd = [config["simulator"], str(config_path)]

            # print(cmd)
            simulation = run(cmd, capture_output=True, text=True, timeout=int(config["timeout"]))

            if simulation.stderr != '' or simulation.stdout == '':
                raise CalledProcessError(simulation.returncode, simulation.args)
            simulation.check_returncode()

            err = float(simulation.stdout.strip().split(':')[2])
        except (CalledProcessError, FileNotFoundError) as e:
            error = simulation.stderr.strip()
            logging.error(f"\"{error}\" => To reproduce that error you can run: {' '.join(cmd)}")
            return str('-inf')
        except TimeoutExpired:
            logging.error(f"Timeout of the sub-process, process got killed {config_path}")
            return str('-inf')
        else:
            try:
                remove(config_path)
            except OSError as e:
                raise e

        return -(err**2)

    def launch(self) -> pd.DataFrame:
        """Launch the search."""
        self.df = self.search.search(max_evals=self.max_evals, timeout=self.deephyper_timeout)

        # Clean the dataframe and re-ordering the columns
        # self.df["workflow"] = self.df.apply(lambda row: Path(
        #     Path(row["workflow"]).name).stem, axis=1)

        self.df = self.df.drop(self.df.filter(
            regex='CAT.*|simulator').columns, axis=1)

        cols = self.df.columns.tolist()

        cols = cols[-4:] + cols[:-4]

        self.df = self.df[cols]
        self.write_csv()

        return self.df

    def get_dataframe(self, simplify=True) -> pd.DataFrame | None:
        """Get the pandas data frame from DeepHyper run and clean it."""
        if simplify:
            # shorten workflow name
            self.df["workflow"] = self.df["workflow"].apply(lambda x: x.split("/")[-1])
        return self.df

    def get_best_row(self) -> pd.DataFrame | None:
        """Return the best configuration."""
        if self.df.empty:
            return None

        i_max = self.df.objective.argmax()

        return self.df.iloc[i_max]

    def get_best_config_json(self) -> JSON:
        """Return the best configuration found as a JSON."""
        if self.df.empty:
            return None

        i_max = self.df.objective.argmax()
        data_start = self.df.iloc[0].to_dict()
        data_best = self.df.iloc[i_max].to_dict()
        runtime = float(data_best["timestamp_gather"]) - float(data_start["timestamp_submit"])

        conf = Calibrator.create_wrench_configuration(data_best)

        conf["calibration"] = {}
        conf["calibration"]["error"] = str(abs(data_best["objective"])**0.5)
        conf["calibration"]["nb_iter"] = str(int(i_max)+1)
        conf["calibration"]["runtime_sec"] = str(runtime)

        return conf

    def write_csv(self, simplify=True) -> None:
        """Write the data frame into a CSV."""
        if simplify:
            # shorten workflow name
            self.df["workflow"] = self.df["workflow"].apply(lambda x: x.split("/")[-1])

        if self.random_search:
            self.df.to_csv(self.output_dir+'/rs.csv', index=False)
        else:
            self.df.to_csv(self.output_dir+'/bo.csv', index=False)

    # def plot(self, show: bool=False):
    #     """Produce a figure of the error in function of the iteration."""
    #     plt.plot(
    #         self.df.objective.cummin(),
    #         label='Objective',
    #         marker='o',
    #         color="blue",
    #         lw=2
    #     )

    #     plt.grid(True)
    #     plt.xlabel("Iterations")
    #     plt.ylabel("Error")
    #     filename = "results.pdf"
    #     plt.savefig(f"{self.output_dir}/{filename}")
    #     if show:
    #         plt.show()

def plot(df_bo: pd.DataFrame, df_rs: pd.DataFrame, output: str, plot_rs: bool=True, show: bool=False):
    """
    Produce a figure of the error in function of the iterations for different methods.
    """
    df_bo["objective"] = 100*(df_bo["objective"].abs()**0.5)
    df_rs["objective"] = 100*(df_rs["objective"].abs()**0.5)

    plt.plot(
        df_bo.objective.cummin(),
        label='Bayesian Optimization',
        marker='o',
        color="blue",
        lw=1
    )

    if plot_rs:
        plt.plot(
            df_rs.objective.cummin(),
            label='Random Search',
            marker='x',
            color="red",
            lw=1
        )

    filename = str(Path(output).stem)
    if filename[-1] == '.':
        filename = filename + "pdf"
    else:
        filename = filename + ".pdf"

    path = Path(output).parent / Path(filename)

    plt.grid(True)
    plt.xlabel("Iterations")
    plt.ylabel("Error (\%)")
    plt.legend()
    plt.savefig(path)
    if show:
        plt.show()

if __name__ == "__main__":

    plt.rcParams.update({
        "text.usetex": True,
        "font.family": "serif",
        "font.serif": ["sans-serif"],
    })

    logger = configure_logger(level = logging.WARNING)

    parser = ArgumentParser(description='Calibrate a WRENCH simulator using DeepHyper.')
    parser.add_argument('--config', '-c', dest='conf', action='store',
                        type=Path, required=True,
                        help='Path to the JSON configuration file')

    parser.add_argument('--docker', '-d', dest='docker', action='store_true',
                        help="Use docker to run the simulator. \
                        The image 'simulator_docker_image' from the JSON config file will be used.")

    parser.add_argument('--workflows', '-w', dest='workflows', nargs='+',
                        type=Path, required=False,
                        help='Path to the workflows (override the paths in the config file)')

    parser.add_argument('--wrench-timeout', '-wt', action='store',
                        type=int, default=300,
                        help='Timeout in seconds for the WRENCH simulator (default 300s)')

    parser.add_argument('--deephyper-timeout', '-dt', action='store',
                        type=int, default=300,
                        help='Timeout in seconds for DeepHyper (default 300s)')

    parser.add_argument('--iter', '-i', dest='iter', action='store',
                        type=int, default=1,
                        help='Number of iterations executed by DeepHyper')

    parser.add_argument('--early-stop', '-e', action='store',
                        help=f'Stop the search after X iterations if the objective has \
                        not improved. By default: no early stop')

    parser.add_argument('--all', '-a', action='store_true',
                        help='Perform a benchmark by running the \
                            same auto-calibration procedure using Bayesian Optimization (BO) \
                            and Random Search (RS). By default the script only uses BO.')

    parser.add_argument('--cores', '-x', dest='cores', action='store',
                        type=int, required=False,
                        help='Number of cores to use (by default all available on the machine)')

    parser.add_argument('--no-properties', action='store_false',
                        help='Calibrate the simulator without properties.')

    parser.add_argument('--no-payloads', action='store_false',
                        help='Calibrate the simulator without payloads.')

    parser.add_argument('--compute-service-scheme', action='store', type=str,
                        help=f'Specify the value of compute_service_scheme in \
                        the configuration. Possible values: all_bare_metal, \
                        htcondor_bare_metal .')

    parser.add_argument('--storage-service-scheme', action='store', type=str,
                        help=f'Specify the value of storage_service_scheme in \
                        the configuration. Possible values: submit_only, submit_and_compute_hosts .')

    parser.add_argument('--network-topology-scheme', action='store', type=str,
                        help=f'Specify the value of network_topology_scheme in \
                        the configuration. Possible values: one_link, one_and_then_many_links, many_links')

    args = parser.parse_args()

    if not args.conf.is_file():
        logger.error(f"Configuration file '{args.conf}' does not exist.")
        exit(1)

    if args.workflows:
        for wf in args.workflows:
            if not wf.is_file():
                logger.error(f"Workflow file '{wf}' does not exist or is not a valid file.")
                exit(1)

    exp_id = "exp-"+str(uuid4()).split('-')[-1]

    try:
        mkdir(exp_id)
        print(f"~~~~~~~~~~~~~~~ {exp_id} ~~~~~~~~~~~~~~~")
    except OSError as e:
        print(e)
        exit(1)

    assert args.compute_service_scheme in [None, "all_bare_metal", "htcondor_bare_metal"]
    assert args.storage_service_scheme in [None, "submit_only", "submit_and_compute_hosts"]
    assert args.network_topology_scheme in [None, "one_link", "one_and_then_many_links", "many_links"]

    # Copy the configuration used
    copyfile(args.conf, f"{exp_id}/setup.json")

    if args.docker:
        # Setup Docker (with cleaning up upon exit)
        with open(args.conf, 'r') as stream:
            docker_image = json.load(stream)["simulator_docker_image"]
        docker_container_id = create_docker_container(docker_image)
        atexit.register(lambda: kill_docker_container(docker_container_id))

    bayesian = Calibrator(
        config=args.conf,
        workflows=args.workflows,
        random_search=False,
        max_evals=args.iter,
        wrench_timeout=args.wrench_timeout,
        deephyper_timeout=args.deephyper_timeout,
        cores=args.cores,
        consider_payloads=args.no_payloads,
        consider_properties=args.no_properties,
        output_dir=exp_id,
        early_stop=args.early_stop,
        compute_service_scheme=args.compute_service_scheme,
        storage_service_scheme=args.storage_service_scheme,
        network_topology_scheme=args.network_topology_scheme,
        logger=logger
    )

    bayesian.launch()
    df_bayesian = bayesian.get_dataframe()
    best_config = bayesian.get_best_config_json()
    bayesian.write_json(best_config, f"{exp_id}/best-bo.json")

    df = pd.DataFrame(
        {
            'exp_id': exp_id,
            'job_id': df_bayesian['job_id'],
            'worklow': df_bayesian['workflow'][0],
            'err_bo': df_bayesian["objective"].abs()**0.5
        }
    )

    is_inf = False
    if args.all:
        baseline = Calibrator(
            config=args.conf,
            workflows=args.workflows,
            random_search=True,
            max_evals=args.iter,
            wrench_timeout=args.wrench_timeout,
            deephyper_timeout=args.deephyper_timeout,
            cores=args.cores,
            consider_payloads=args.no_payloads,
            consider_properties=args.no_properties,
            output_dir=exp_id,
            early_stop=args.early_stop,
            compute_service_scheme=args.compute_service_scheme,
            storage_service_scheme=args.storage_service_scheme,
            network_topology_scheme=args.network_topology_scheme,
            logger=logger
        )

        baseline.launch()
        df_baseline = baseline.get_dataframe()
        best_config = baseline.get_best_config_json()
        baseline.write_json(best_config, f"{exp_id}/best-rs.json")

        df = pd.DataFrame(
            {
                'exp_id': exp_id,
                'job_id': df_bayesian["job_id"],
                'worklow': df_bayesian['workflow'][0],
                'err_bo': df_bayesian["objective"].abs()**0.5,
                'err_rs': df_baseline["objective"].abs()**0.5,
            }
        )
        is_inf = np.isinf(df['err_rs']).any()

    if not np.isinf(df['err_bo']).any():
        print(f"=============== {exp_id} ===============")
        print(f"Best error:")
        print("\tBayesian Optimization    (BO): {:.3%}".format(
            min(df['err_bo'])))
    if args.all and not is_inf:
        print("\tRandom Search - baseline (RS): {:.3%}".format(
            min(df['err_rs'])))

    if not (np.isinf(df['err_bo']).any() and is_inf):
        # Plot
        plot(df_bayesian, df_baseline, output=f"{exp_id}/results.pdf",
             plot_rs=args.all, show=False)
        # Save data
        df.to_csv(f"{exp_id}/global-results.csv", index=False)
