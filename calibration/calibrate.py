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

if sys.version_info[0] != 3 or sys.version_info[1] >= 10:
    print(
        f"ERROR: This script requires Python <3.10, >=3.7. \
        You are using Python {sys.version_info[0]}.{sys.version_info[1]}")
    sys.exit(-1)

import os
import atexit
import time
import re
import json
import logging
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt

from os import mkdir, remove, environ
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
from deephyper.evaluator.callback import LoggerCallback, SearchEarlyStopping
from deephyper.evaluator import Evaluator
from deephyper.problem import HpProblem
from ConfigSpace import EqualsCondition
from ConfigSpace.hyperparameters import CategoricalHyperparameter, UniformIntegerHyperparameter

plt.rcParams.update({
    "text.usetex": True,
    "font.family": "serif",
    "font.serif": ["sans-serif"],
})

# Mandatory to load the simulator if SimGrid and WRENCH shared lib
# are not located in /usr/local/lib
if sys.platform == "darwin":
    if "DYLD_LIBRARY_PATH" not in environ:
        environ["DYLD_LIBRARY_PATH"] = ""
    environ["DYLD_LIBRARY_PATH"] = environ["DYLD_LIBRARY_PATH"] +":" + environ["HOME"] + "/local/lib/"

SCHEMES = {"error": "error_computation_scheme",
           "compute": "compute_service_scheme",
           "storage": "storage_service_scheme",
           "network": "network_topology_scheme"}

# Docker container ID as a global variable
docker_container_id = ""

# Some values are expressed as power of 2 to reduce the space of solutions:
#   if MAX_PAYLOADS_VAL = 5 and MIN_PAYLOADS_VAL=0 then we the space explored 
#   will consist of [1, 2, 4, 8, 16, 32]

######################## General parameters ###########################
MIN_SCHED_OVER                  = 0        # min is 2^0 = 1 ms
MAX_SCHED_OVER                  = 10       # max is 2^10 = 1024 ms
#################### Platform-related parameters ######################
MIN_CORES                       = 0        # min is 2^3 = 1 core/host
MAX_CORES                       = 8        # max is 2^8 = 256 core/host
MIN_HOSTS                       = 0        # min is 2^3 = 1 host
MAX_HOSTS                       = 7        # max is 2^8 = 256 hosts
MIN_PROC_SPEED                  = 3        # min is 2^3 = 8 Gflops
MAX_PROC_SPEED                  = 8        # max is 2^8 = 256 Gflops
MIN_BANDWIDTH                   = 6        # min is 2^6 = 64 MBps
MAX_BANDWIDTH                   = 17       # max is 2^17 = 128 GBps
MIN_LATENCY                     = 0        # min is 2^0 = 1 us
MAX_LATENCY                     = 12       # max is 2^12 = 4096 us
#################### Payloads-related parameters ######################
MIN_PAYLOADS_VAL                = 0        # min is 2^0 = 1 B
MAX_PAYLOADS_VAL                = 20       # max is 2^20 = 1024 KB
#################### Properties-related parameters ####################
SCHEDULING_ALGO                 = ["fcfs",
                                   "conservative_bf",
                                   "conservative_bf_core_level"]
MIN_BUFFER_SIZE                 = 20
MAX_BUFFER_SIZE                 = 30
MIN_CONCURRENT_DATA_CONNECTIONS = 1
MAX_CONCURRENT_DATA_CONNECTIONS = 64
#######################################################################
SAMPLING = "uniform"
EARLY_STOP = 20
#######################################################################

JSON = Union[Dict[str, Any], List[Any], int, str, float, bool, Type[None]]

# To shutdown  FutureWarning: The frame.append method is deprecated 
# and will be removed from pandas in a future version. Use pandas.concat instead.
filterwarnings("ignore", category=FutureWarning)

def configure_logger(level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(__name__)
    # create console handler and set level to debug
    ch = logging.StreamHandler()
    # create formatter
    formatter = logging.Formatter(
        '[%(levelname)s(%(asctime)s)][%(filename)s:%(lineno)s/%(funcName)s] - %(message)s',
        datefmt='%Y:%m:%d-%I:%M:%S'
    )
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    logger.setLevel(level)
    return logger



def create_docker_container(docker_image) -> str:
    """
    Create a Docker container to run the simulator.
    Returns the container ID.
    """

    logger.info(f"Starting Docker container for image {docker_image}")
    cmd = "docker run -it -d -v " + os.getcwd() + ":/home/wrench " + docker_image
    docker = run(cmd.split(" "), capture_output=True, text=True, timeout=int(10))
    if docker.stdout == '':
        raise CalledProcessError(docker.returncode, docker.args)
    docker.check_returncode()
    global docker_container_id
    docker_container_id = docker.stdout.strip()
    logger.info(f"Docker container started ({docker_container_id[0:11]})")
    return docker.stdout.strip()



def kill_docker_container(docker_container_id: str) -> str:
    """Kill a Docker container."""
    logger.info(f"Waiting for Docker container to idle...")
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
    logger.info(f"Killing Docker container ({docker_container_id[0:11]})...")
    cmd = "docker kill " + docker_container_id
    docker = run(cmd.split(" "), capture_output=True, text=True, timeout=int(10))
    docker.check_returncode()
    logger.info("Docker container killed")
    time.sleep(1)
    cmd = "docker rm " + docker_container_id
    docker = run(cmd.split(" "), capture_output=True, text=True, timeout=int(10))
    docker.check_returncode()
    logger.info("Docker container removed")


def get_nested_default(d: dict, path: str):
    return reduce(lambda d, k: d.setdefault(k, {}), path, d)

def set_nested(d: dict, path :str, value: str):
    get_nested_default(d, path[:-1])[path[-1]] = value

def get_val_with_unit(path: List[str], val: any) -> str:
    updated_val = str(val)
    if path[-1] == "speed":
        updated_val = str(2**int(val))+"Gf"
    elif "bandwidth" in path[-1] or "disk" in path[-1]:
        updated_val = str(2**int(val))+"MBps"
    elif "latency" in path[-1]:
        updated_val = str(2**int(val))+"us"
    elif "OVERHEAD" in path[-1] or "DELAY" in path[-1]:
        updated_val = str(2**int(val))+"ms"
    elif "BUFFER_SIZE" in path[-1]:
        updated_val = "infinity" if isnan(val) else str(2**int(val))
    elif "MAX_NUM_CONCURRENT_DATA_CONNECTIONS" in path[-1]:
        updated_val = "infinity" if isnan(val) else str(int(val))
    else:
        try:
            updated_val = str(2**int(val))
        except ValueError as e:
            pass
    return updated_val


"""
    Create a platform file and a WRENCH configuration based on what DeepHyper picked.
"""

def setup_configuration(config: Dict) -> Dict:

    wrench_conf = {}
    param_names = [x+"_parameters" for x in SCHEMES.values()]

    wrench_conf["workflow"] = {}
    wrench_conf["workflow"]["file"] = config["workflow"]
    wrench_conf["workflow"]["reference_flops"] = str(config["reference_flops"])

    wrench_conf["scheduling_overhead"] = str(
        2**int(config["scheduling_overhead"]))+"ms"

    for val in SCHEMES.values():
        wrench_conf[val] = config[val]
        wrench_conf[val+"_parameters"] = {}
        wrench_conf[val+"_parameters"][config[val]] = {}

    for key, val in config.items():
        path = key.split('-')
        if path[0] in param_names:
            updated_val = get_val_with_unit(path, val)
            set_nested(wrench_conf, path, updated_val)

    # print(json.dumps(wrench_conf, indent=4))

    return wrench_conf




def worker(config: Dict) -> float:
    """
    Launch one instance of a simulator in one subprocess
    based on a given configuration/platform.
    """
    err = 0.0
    logger = logging.getLogger(__name__)

    config_path = Path(f"{config['output_dir']}/config-{config['job_id']}.json")
    wrench_conf: Dict = setup_configuration(config)
    use_docker: bool = "docker_container_id" in config

    # We write the configuration we got from DeepHyper as a JSON file for the simulator
    with open(config_path, 'w') as temp_config:
        json_config = json.dumps(wrench_conf, indent=4)
        temp_config.write(json_config)
    try:
        if use_docker:
            cmd = ["docker", "exec", config["docker_container_id"], config["simulator"], str(config_path)]
        else:
            cmd = [config["simulator"], str(config_path)]

        simulation = run(cmd, capture_output=True, text=True, timeout=int(config["timeout"]))

        if simulation.stderr != '' or simulation.stdout == '':
            raise CalledProcessError(simulation.returncode, simulation.args)
        simulation.check_returncode()

        err = float(simulation.stdout.strip().split(':')[2])
    except (CalledProcessError, FileNotFoundError) as e:
        error = simulation.stderr.strip()
        logger.error(error)
        logger.error(f"To reproduce that error you can run: {' '.join(cmd)}")
        return str('-inf')
    except TimeoutExpired:
        logger.error(f"Timeout of the subprocess, process got killed {config_path}")
        return str('-inf')
    else:
        try:
            remove(config_path)
        except OSError as e:
            raise e

    return -(err**2)


class Calibrator(object):
    """
    This class defines a WRENCH simulation auto-calibrator

    :param config: Path for the configuration file (JSON)
    :type config: Path
    :param workflows: A list of workflows calibrate together, defaults to [None]. 
    If None, the workflow(s) found in the config file will be used.
    :type workflows: List[Path]
    :param random_search: Perform a random search instead of a bayesian optimization, defaults to [False]
    :type random_search: bool
    :param max_evals: Number of iterations performed, defaults to [100]
    :type max_evals: int
    :param cores: Number of workers used (by default: all available = number of physical cores), defaults to [None]
    :type cores: int
    :param timeout: Seconds after which the simulator is killed for each iteration (if None = infinite), defaults to [None]
    :type timeout: int
    :param consider_properties: Calibrate properties, defaults to [True]
    :type consider_properties: Path
    :param consider_payloads: Calibrate payloads, defaults to [True]
    :type consider_payloads: bool
    :param output_dir: Output directory for all the files, defaults to [None]
    :type output_dir: str
    :param early_stop: If true DeepHyper will stop the exploration of the objective has not improved after X iterations, defaults to [True]
    :type early_stop: bool
    :param compute_service_scheme: Specify the compute_service_scheme to use, defaults to [None]
    :type compute_service_scheme: str
    :param storage_service_scheme: Specify the storage_service_scheme to use, defaults to [None]
    :type storage_service_scheme: str
    :param network_topology_scheme: Specify the network_topology_scheme to use, defaults to [None]
    :type network_topology_scheme: str
    :param use_docker: use Docker to run the simulator, defaults to [False]
    :type use_docker: bool
    :param docker_container_id: The Docker container ID if running with Docker, defaults to [None]
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
                timeout: int = None,
                consider_properties: bool = True,
                consider_payloads: bool = True,
                output_dir: str = None,
                early_stop: bool = True,
                compute_service_scheme: str = None,
                storage_service_scheme: str = None,
                network_topology_scheme: str = None,
                use_docker: bool = False,
                docker_container_id: str = None,
                logger: logging.Logger = None) -> None:

        self.logger = logger if logger else logging.getLogger(__name__)
        self.config: JSON = self._load_json(config)
        self.random_search = random_search
        self.max_evals = max_evals
        self.timeout = timeout
        self.output_dir = output_dir
        self.early_stop = early_stop
        self.compute_service_scheme = compute_service_scheme
        self.storage_service_scheme = storage_service_scheme
        self.network_topology_scheme = network_topology_scheme
        self.use_docker = use_docker
        self.docker_container_id = docker_container_id
        self.consider_payloads = consider_payloads
        self.consider_properties = consider_properties

        self.problem = HpProblem()

        self.func = worker
        if cores:
            self.num_cpus = cores
        else:
            self.num_cpus = min(self.max_evals, int(cpu_count(logical=False)))

        #Use subprocess as backend, to use ThreadPool -> thread 
        self.backend = "process"
        # Number of jobs used to compute the surrogate model ( -1 means max possible)
        self.n_jobs = -1

        self.simulator = self.config["simulator"]

        self.logger.info(f"Trying to run {self.simulator} --version...")
        simu_ok = self._test_simulator(use_docker=self.use_docker)

        if simu_ok[0]:
            self.logger.info(f"Success")
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
                self.logger.info(f"Calibrating {wf}")
            else:
                self.logger.error(f"The file {wf} does not exist.")
                exit(1)

        if self.consider_properties:
            self.logger.info(f"We are calibrating properties")
        if self.consider_payloads:
            self.logger.info(f"We are calibrating payloads.")

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

        callbacks = [LoggerCallback()]
        # Stop after EARLY_STOP evaluations that did not improve the search
        if self.early_stop:
            callbacks.append(SearchEarlyStopping(patience=EARLY_STOP))

        # define the evaluator to distribute the computation
        self.evaluator = Evaluator.create(
            self.func,
            method=self.backend,
            method_kwargs={
                "num_workers": self.num_cpus,
                "callbacks": callbacks
            },
        )

        self.logger.info(f"Evaluator has {self.evaluator.num_workers} available workers")

        if self.random_search:
            # When surrogate_model=DUMMY it performs a Random Search
            self.search = CBO(
                problem=self.problem,
                evaluator=self.evaluator,
                n_jobs=self.n_jobs,
                surrogate_model="DUMMY",
                log_dir=self.output_dir
            )
        else:
            self.search = CBO(
                problem=self.problem,
                evaluator=self.evaluator,
                n_jobs=self.n_jobs,
                surrogate_model="RF",
                log_dir=self.output_dir
            )

    def _add_parameter(self, name: str) -> None:
        line = name.split("-")
        if "core" in line[2]:
            self.problem.add_hyperparameter((MIN_CORES, MAX_CORES, SAMPLING),name)
        elif "host" in line[2]:
            self.problem.add_hyperparameter(
                (MIN_HOSTS, MAX_HOSTS, SAMPLING), name)
        elif "speed" in line[2]:
            self.problem.add_hyperparameter((MIN_PROC_SPEED, MAX_PROC_SPEED, SAMPLING),name)
        elif "bandwidth" in line[2]:
            self.problem.add_hyperparameter(
                (MIN_BANDWIDTH, MAX_BANDWIDTH, SAMPLING), name)
        elif "disk" in line[2]:
            self.problem.add_hyperparameter(
                (MIN_BANDWIDTH, MAX_BANDWIDTH, SAMPLING), name)
        elif "payload" in line[2]:
            self.problem.add_hyperparameter(
                (MIN_PAYLOADS_VAL, MAX_PAYLOADS_VAL, SAMPLING), name)
        elif "latency" in line[2]:
            self.problem.add_hyperparameter(
                (MIN_LATENCY, MAX_LATENCY, SAMPLING), name)
        elif "properties" in line[2]:
            l = name.split('::')
            if "OVERHEAD" in l[-1] or "DELAY" in l[-1]:
                self.problem.add_hyperparameter(
                    (MIN_SCHED_OVER, MAX_SCHED_OVER, SAMPLING), name)
            elif "BATCH_SCHEDULING_ALGORITHM" == l[-1]:
                self.problem.add_hyperparameter(SCHEDULING_ALGO, name)
            elif "BUFFER_SIZE" == l[-1]:
                # Model the concurrent access/buffer size with two variables:
                # - inf or not inf
                #   - if not inf we pick a discrete value between MIN and MAX
                buffer_size_categorical = CategoricalHyperparameter(
                    "CAT_"+name, choices=["infinity", "finite"])
                # Express as power of 2^x : if range goes to 8 to 10 then the values will range from 2^8 to 2^10
                buffer_size_discrete = UniformIntegerHyperparameter(
                    name, lower=MIN_BUFFER_SIZE, upper=MAX_BUFFER_SIZE, log=False)
                self.problem.add_hyperparameter(
                    buffer_size_categorical)
                self.problem.add_hyperparameter(
                    buffer_size_discrete)
                # If we choose "finite" then we sample a discrete value for the buffer size
                self.problem.add_condition(EqualsCondition(
                    buffer_size_discrete, buffer_size_categorical, "finite"))
            elif "MAX_NUM_CONCURRENT_DATA_CONNECTIONS" == l[-1]:
                conc_conn_categorical = CategoricalHyperparameter(
                    "CAT_"+name, choices=["infinity", "finite"])
                conc_conn_discrete = UniformIntegerHyperparameter(
                    name, lower=MIN_CONCURRENT_DATA_CONNECTIONS, upper=MAX_CONCURRENT_DATA_CONNECTIONS, log=False)
                self.problem.add_hyperparameter(conc_conn_categorical)
                self.problem.add_hyperparameter(conc_conn_discrete)
                self.problem.add_condition(EqualsCondition(
                    conc_conn_discrete, conc_conn_categorical, "finite"))
        else:
            logger.warn(f"Did not find how to add parameter {name}")
            return None

        logger.info(f"Added parameter {line[-1]} for calibration.")


    def add_parameters(self):
        self.problem.add_hyperparameter([str(self.simulator)], "simulator")
        self.problem.add_hyperparameter([str(wf) for wf in self.workflows], "workflow")
        self.problem.add_hyperparameter([str(self.output_dir)], "output_dir")
        self.problem.add_hyperparameter([str(self.timeout)], "timeout")
        if self.use_docker:
            self.problem.add_hyperparameter([str(self.docker_container_id)], "docker_container_id")

        for scheme in self.schemes.values():
            self.problem.add_hyperparameter(
                [self.simulator_config[scheme]], scheme)

        self.problem.add_hyperparameter([str(self.simulator_config["workflow"]["reference_flops"])], "reference_flops")
        self.problem.add_hyperparameter(
            (MIN_SCHED_OVER, MAX_SCHED_OVER, SAMPLING), "scheduling_overhead")

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

    """
        Test the simulator to make sure it exists and that's a valid WRENCH simulator
    """

    def _test_simulator(self, use_docker: bool) -> Tuple[bool, str]:
        if use_docker:
            cmd = ["docker", "exec", self.docker_container_id, self.simulator, "--version"]
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

    """
        Load the JSON file that define the experiments
    """

    def _load_json(self, path: Path) -> JSON:
        with open(path, 'r') as stream:
            return json.load(stream)

    """
        Write a dict in a JSON file
    """

    def write_json(self, data: JSON, path: Path) -> None:
        with open(path, 'w') as f:
            json_data = json.dumps(data, indent=4)
            f.write(json_data)

    """
        Launch the search.
    """

    def launch(self) -> pd.DataFrame:
        self.df = self.search.search(max_evals=self.max_evals, timeout=self.timeout)

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

    """
        Get the pandas data frame
    """

    def get_dataframe(self, simplify=True) -> pd.DataFrame | None:
        if simplify:
            # shorten workflow name
            self.df["workflow"] = self.df["workflow"].apply(lambda x: x.split("/")[-1])
        return self.df

    """
        Return the best configuration
    """

    def get_best_row(self) -> pd.DataFrame | None:
        if self.df.empty:
            return None

        i_max = self.df.objective.argmax()

        return self.df.iloc[i_max]

    """
        Return the best configuration found as a JSON
    """

    def get_best_config_json(self) -> JSON:
        if self.df.empty:
            return None

        i_max = self.df.objective.argmax()
        data = self.df.iloc[i_max].to_dict()

        conf = setup_configuration(data)

        conf["calibration"] = {}
        conf["calibration"]["error"] = str(abs(data["objective"])**0.5)
        conf["calibration"]["timestamp_submit"] = str(data["timestamp_submit"])
        conf["calibration"]["timestamp_gather"] = str(data["timestamp_gather"])

        return conf

    """
        Write the data frame into a CSV
    """

    def write_csv(self, simplify=True) -> None:
        if simplify:
            # shorten workflow name
            self.df["workflow"] = self.df["workflow"].apply(lambda x: x.split("/")[-1])

        if self.random_search:
            self.df.to_csv(self.output_dir+'/rs.csv', index=False)
        else:
            self.df.to_csv(self.output_dir+'/bo.csv', index=False)

    """
        Produce a figure of the error in function of the iteration
    """

    def plot(self, show: bool = False):
        plt.plot(
            self.df.objective,
            label='Objective',
            marker='o',
            color="blue",
            lw=2
        )

        plt.grid(True)
        plt.xlabel("Iterations")
        plt.ylabel("Error")
        filename = "results.pdf"
        plt.savefig(f"{self.output_dir}/{filename}")
        if show:
            plt.show()

"""
    Produce a figure of the error in function of the iterations for different methods
"""

def plot(df: pd.DataFrame, output: str, plot_rs: bool = True, show: bool = False):
    plt.plot(
        df.err_bo,
        label='Bayesian Optimization',
        marker='o',
        color="blue",
        lw=1
    )

    if plot_rs:
        plt.plot(
            df.err_rs,
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


    logger = configure_logger(level=logging.INFO)

    parser = ArgumentParser(description='Calibrate a WRENCH simulator using DeepHyper.')
    parser.add_argument('--config', '-c', dest='conf', action='store',
                        type=Path, required=True,
                        help='Path to the JSON configuration file'
                        )

    parser.add_argument('--docker', '-d', dest='docker', action='store_true',
                        help="Use docker to run the simulator. \
                        The image 'simulator_docker_image' from the JSON config file will be used."
    )

    parser.add_argument('--workflows', '-w', dest='workflows', nargs='+',
                        type=Path, required=False,
                        help='Path to the workflows (override the paths in the config file)'
    )

    parser.add_argument('--iter', '-i', dest='iter', action='store',
                        type=int, default=1,
                        help='Number of iterations executed by DeepHyper'
    )

    parser.add_argument('--no-early-stopping', '-e', action='store_false',
                        help=f'Do not stop the search when it does not improve for a given \
                        number (here {EARLY_STOP}) of evaluations. Keep doing all the iterations even \
                        if it does not improve the objective.'
    )

    parser.add_argument('--all', '-a', action='store_true',
                        help='Perform a benchmark by running the \
                            same auto-calibration procedure using Bayesian Optimization (BO) \
                            and Random Search (RS). By default the script only uses BO.'
    )

    parser.add_argument('--cores', '-x', dest='cores', action='store',
                        type=int, required=False,
                        help='Number of cores to use (by default all available on the machine)'
    )

    parser.add_argument('--no-properties', action='store_false',
                        help='Calibrate the simulator without properties.'
    )

    parser.add_argument('--no-payloads', action='store_false',
                        help='Calibrate the simulator without payloads.'
    )

    parser.add_argument('--compute-service-scheme', action='store', type=str,
                        help=f'Specify the value of compute_service_scheme in \
                        the configuration. Possible values: all_bare_metal, \
                        htcondor_bare_metal .'
    )

    parser.add_argument('--storage-service-scheme', action='store', type=str,
                        help=f'Specify the value of storage_service_scheme in \
                        the configuration. Possible values: submit_only, submit_and_compute_hosts .'
    )

    parser.add_argument('--network-topology-scheme', action='store', type=str,
                        help=f'Specify the value of network_topology_scheme in \
                        the configuration. Possible values: one_link, one_and_then_many_links, many_links'
    )

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
        timeout=300,  # 5 min timeout
        cores=args.cores,
        consider_payloads=args.no_payloads,
        consider_properties=args.no_properties,
        output_dir=exp_id,
        early_stop=args.no_early_stopping,
        compute_service_scheme=args.compute_service_scheme,
        storage_service_scheme=args.storage_service_scheme,
        network_topology_scheme=args.network_topology_scheme,
        use_docker=args.docker,
        docker_container_id=docker_container_id,
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

    if args.all:
        baseline = Calibrator(
            config=args.conf,
            workflows=args.workflows,
            random_search=True,
            max_evals=args.iter,
            timeout=300,  # 5 min timeout
            cores=args.cores,
            consider_payloads=args.no_payloads,
            consider_properties=args.no_properties,
            output_dir=exp_id,
            early_stop=args.no_early_stopping,
            compute_service_scheme=args.compute_service_scheme,
            storage_service_scheme=args.storage_service_scheme,
            network_topology_scheme=args.network_topology_scheme,
            use_docker=args.docker,
            docker_container_id=docker_container_id,
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

    print(f"=============== {exp_id} ===============")
    print(f"Best error:")
    print("\tBayesian Optimization    (BO): {:.3%}".format(
        min(df['err_bo'])))
    if args.all:
        print("\tRandom Search - baseline (RS): {:.3%}".format(
            min(df['err_rs'])))

    # Plot
    plot(df*100, output=f"{exp_id}/results.pdf",
         plot_rs=args.all, show=False)
    # Save data
    df.to_csv(f"{exp_id}/global-results.csv", index=False)
