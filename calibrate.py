#!/usr/bin/env python3.9
#
# Copyright (c) 2022. Loïc Pottier <lpottier@isi.edu>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from __future__ import annotations
import warnings
import xml.etree.ElementTree as ET
import pandas as pd
import argparse
import os
import uuid
import pathlib
import logging
import subprocess
import json
import psutil
import shutil
from typing import Dict, List, Any, Union, Type, Tuple
from deephyper.search.hps import AMBS
from deephyper.evaluator.callback import LoggerCallback
from deephyper.evaluator import Evaluator
from deephyper.problem import HpProblem
import ConfigSpace as CS
import ConfigSpace.hyperparameters as CSH
import matplotlib.pyplot as plt

# Some values are expressed as power of 2 to reduce the space of solutions:
#   if MAX_PAYLOADS_VAL = 5 and MIN_PAYLOADS_VAL=0 then we the space explored will consist of [1, 2, 4, 8, 16, 32]

########### General parameters ###########
MIN_REF_FLOPS = 3      # min is 2^3 = 8 Gflops
MAX_REF_FLOPS = 8      # max is 2^8 = 256 Gflops
MIN_SCHED_OVER = 0     # min is 2^0 = 1 seconde
MAX_SCHED_OVER = 6     # max is 2^6 = 32 secondes
########### Platform-related parameters ###########
MIN_PROC_SPEED = 3     # min is 2^3 = 8 Gflops
MAX_PROC_SPEED = 8     # max is 2^8 = 256 Gflops
MIN_DISK_IO = 6        # min is 2^6 = 64 MBps
MAX_DISK_IO = 10       # max is 2^10 = 1024 MBps
MIN_BANDWIDTH = 6      # min is 2^6 = 64 MBps
MAX_BANDWIDTH = 17     # max is 2^17 = 128 GBps
MIN_LATENCY = 0        # min is 2^0 = 1 us
MAX_LATENCY = 12       # max is 2^12 = 4096 us
########### Payloads-related parameters ###########
MIN_PAYLOADS_VAL = 0   # min is 2^0 = 1 B
MAX_PAYLOADS_VAL = 20  # max is 2^20 = 1024 KB
########## Properties-related parameters ##########
SCHEDULING_ALGO = ["fcfs", "conservative_bf", "conservative_bf_core_level"]
# TASK_SELECTION_ALGORITHM = ["maximum_flops",
#                             "maximum_minimum_cores", "minimum_top_level"]
# # Warning: only makes sense if SCHEDULING_ALGO = "fcfs" (cf WRENCH documentation)
# HOST_SELECTION_ALGORITHM = ["FIRSTFIT", "BESTFIT", "ROUNDROBIN"]
###################################################
SAMPLING = "uniform"
###################################################

JSON = Union[Dict[str, Any], List[Any], int, str, float, bool, Type[None]]

# To shutdown  FutureWarning: The frame.append method is deprecated and will be removed from pandas in a future version. Use pandas.concat instead.
warnings.filterwarnings("ignore", category=FutureWarning)

plt.rcParams.update({
    "text.usetex": True,
    "font.family": "serif",
    "font.serif": ["sans-serif"],
})

"""
    Produce a figure of the error in function of the iterations for different methods
"""


def plot(df: pd.DataFrame, output: str, plot_rs: bool = True, show: bool = False):
    plt.plot(df.err_bo,
             label='Bayesian Optimization',
             marker='o',
             color="blue",
             lw=1)

    if plot_rs:
        plt.plot(df.err_rs,
                 label='Random Search',
                 marker='x',
                 color="red",
                 lw=1)

    filename = str(pathlib.Path(output).stem)
    if filename[-1] == '.':
        filename = filename + "pdf"
    else:
        filename = filename + ".pdf"

    path = pathlib.Path(output).parent / pathlib.Path(filename)

    plt.grid(True)
    plt.xlabel("Iterations")
    plt.ylabel("Error (\%)")
    plt.legend()
    plt.savefig(path)
    if show:
        plt.show()


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


def create_platform(xml_file: str, config: Dict, new_xml: str) -> None:
    data = ET.parse(xml_file)
    for elem in data.getroot()[0]:
        if elem.tag == 'host':
            elem.attrib["speed"] = config["speed"]
            for prop in elem:
                if prop.tag == 'disk':
                    prop.attrib["read_bw"] = config["read_bw"]
                    prop.attrib["write_bw"] = config["write_bw"]
        elif elem.tag == 'link':
            elem.attrib["bandwidth"] = config["bandwidth"]
            elem.attrib["latency"] = config["latency"]

    with open(new_xml, 'wb') as f:
        f.write('<?xml version="1.0"?>\n<!DOCTYPE platform SYSTEM "http://simgrid.gforge.inria.fr/simgrid/simgrid.dtd" >\n'.encode('utf8'))
        data.write(f, 'utf-8')

"""
    Create a platform file and a WRENCH configuration based on what DeepHyper picked.
"""


def setup_configuration(config: Dict) -> Dict:
    wrench_conf = {}

    wrench_conf["workflow"] = {}
    wrench_conf["workflow"]["file"] = config["workflow"]
    wrench_conf["workflow"]["reference_flops"] = str(
        2**int(config["speed"]))+"Gf"

    wrench_conf["platform"] = {}
    wrench_conf["platform"]["file"] = config["platform"]

    wrench_conf["compute_service_scheme"] = config["compute_service_scheme"]
    wrench_conf["storage_service_scheme"] = config["storage_service_scheme"]

    wrench_conf["scheduling_overhead"] = float(2**int(config["latency"]))

    if "calib_platform" in config:
        platform_path = pathlib.Path(
            f"{config['output_dir']}/platform-{config['id']}.xml").resolve()

        platform_config = {}
        platform_config["speed"]     = str(2**int(config["speed"]))+"Gf"
        platform_config["read_bw"]   = str(2**int(config["read_bw"]))+"MBps"
        platform_config["write_bw"]  = str(2**int(config["write_bw"]))+"MBps"
        platform_config["bandwidth"] = str(2**int(config["bandwidth"]))+"GBps"
        platform_config["latency"]   = str(2**int(config["latency"]))+"us"
        create_platform(
            xml_file = config["platform"],
            config = platform_config,
            new_xml = str(platform_path)
        )
        wrench_conf["platform"]["file"] = str(platform_path)

    possible_payloads_keys = ["compute_service_message_payloads",
                         "storage_service_message_payloads"]
    for key in possible_payloads_keys:
        wrench_conf[key] = {}

    possible_properties_keys = ["compute_service_properties",
                         "storage_service_properties"]
    for key in possible_properties_keys:
        wrench_conf[key] = {}

    if "calib_properties" in config:
        for k, val in config.items():
            l = k.split('::')
            for key in possible_properties_keys:
                if key == l[0]:
                    if l[1] not in wrench_conf[key]:
                        wrench_conf[key][l[1]] = {}
                    if l[2] == "MAX_NUM_CONCURRENT_DATA_CONNECTIONS":
                        if config["MAX_NUM_CONCURRENT_CAT"] == "infinity":
                            wrench_conf[key][l[1]][l[2]] = "infinity"
                        else:
                            wrench_conf[key][l[1]][l[2]] = str(int(val))
                    elif l[2] == "BUFFER_SIZE":
                        #TODO: # check if val is nan !
                        if config["BUFFER_SIZE_CAT"] == "infinity":
                            wrench_conf[key][l[1]][l[2]] = "infinity"
                        else:
                            wrench_conf[key][l[1]][l[2]] = str(2**int(val))
                    else:
                        wrench_conf[key][l[1]][l[2]] = str(2**int(val))

    if "calib_payloads" in config:
        for k, val in config.items():
            l = k.split('::')
            for key in possible_payloads_keys:
                if key == l[0]:
                    if l[1] not in wrench_conf[key]:
                        wrench_conf[key][l[1]] = {}
                    wrench_conf[key][l[1]][l[2]] = float(2**int(val))

    return wrench_conf


"""
    Launch one instance of a simulator in one process based on a given configuration/platform.
"""

def worker(config: Dict) -> float:
    err = 0.0
    config_path = pathlib.Path(
        f"{config['output_dir']}/config-{config['id']}.json").resolve()
    wrench_conf: Dict = setup_configuration(config)

    # if config['id'] == '1':
    #     print(json.dump(wrench_conf))

    with open(config_path, 'w') as temp_config:
        json_config = json.dumps(wrench_conf, indent=4)
        temp_config.write(json_config)
    try:
        cmd = [config["simulator"], str(config_path)]
        simulation = subprocess.run(
            cmd, capture_output=True, text=True, check=True)
        err = float(simulation.stdout.strip().split(':')[2])
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"[Error] Try to run: {' '.join(cmd)}")
        raise e
    finally:
        try:
            os.remove(config_path)
            os.remove(wrench_conf["platform"]["file"])
        except OSError as e:
            exit(-1)

    return -(err**2)


class Calibrator(object):
    """
        This class defines a WRENCH simulation auto-calibrator
    """

    def __init__(self,
                 config: pathlib.Path,
                 random_search: bool = False,
                 max_evals: int = 100,
                 timeout: int = None,
                 consider_properties: bool = False,
                 consider_payloads: bool = False,
                 output_dir: str = None,
                 logger: logging.Logger = None
                 ) -> None:

        self.logger = logger if logger else logging.getLogger(__name__)
        self.config: JSON = self._load_json(config)
        self.random_search = random_search
        self.max_evals = max_evals
        self.timeout = timeout
        self.output_dir = output_dir

        self.func = worker
        self.num_cpus = min(self.max_evals, int(
            psutil.cpu_count(logical=False)))
        self.num_cpus_per_task = int(
            psutil.cpu_count() // psutil.cpu_count(logical=False)
        )
        self.backend = "ray"
        # Number of jobs used to compute the surrogate model ( -1 means max possible)
        self.n_jobs = -1

        self.simulator: pathlib.Path = pathlib.Path(self.config["simulator"]).resolve()

        self.logger.info(f"Trying to run {self.simulator} --version...")
        simu_ok = self._test_simulator()

        if simu_ok[0]:
            self.logger.info(f"Success")
        else:
            self.logger.error(f"Failed to run the simulator \
                (make sure \'poseidon-sim\' exists, is in the $PATH \
                    or that Docker is running)")
            exit(1)
        
        self.simulator_config: JSON = self._load_json(self.config["config"])

        self.workflow: pathlib.Path = pathlib.Path(
            self.simulator_config["workflow"]["file"]).resolve()
        self.platform: pathlib.Path = pathlib.Path(
            self.simulator_config["platform"]["file"]).resolve()

        self.df: pd.DataFrame = {}  # Result
        if self.output_dir:
            self.csv_output: pathlib.Path = pathlib.Path(self.output_dir)
        else:
            self.output_dir = '.'

        self.problem = HpProblem()
        self.add_basic_parameters()
        self.add_platform_parameters()

        self.consider_payloads = consider_payloads
        self.consider_properties = consider_properties
        # Add  parameters to the search space
        if self.consider_payloads:
            self.add_payloads_parameters()
        if self.consider_properties:
            self.add_properties_parameters()

        # define the evaluator to distribute the computation
        self.evaluator = Evaluator.create(
            self.func,
            method=self.backend,
            method_kwargs={
                "num_cpus": self.num_cpus,
                "num_cpus_per_task": self.num_cpus_per_task,
                "callbacks": [LoggerCallback()]
            },
        )
        self.logger.info(
            f"Evaluator has {self.evaluator.num_workers} available workers")
        if consider_properties:
            self.logger.info(
                f"We are using properties in addition of payloads.")

        if self.random_search:
            # When surrogate_model=DUMMY it performs a Random Search
            self.search = AMBS(
                problem=self.problem,
                evaluator=self.evaluator,
                n_jobs=self.n_jobs,
                surrogate_model="DUMMY",
                log_dir=self.output_dir
            )
        else:
            self.search = AMBS(
                problem=self.problem,
                evaluator=self.evaluator,
                n_jobs=self.n_jobs,
                log_dir=self.output_dir
            )

    def add_basic_parameters(self):
        # For convenience (not real hyperparameter)
        # We add them to the hyperparameter dict so we can have access to these variables inside each worker
        self.problem.add_hyperparameter([str(self.simulator)], "simulator")
        self.problem.add_hyperparameter([str(self.workflow)], "workflow")
        self.problem.add_hyperparameter([str(self.platform)], "platform")
        self.problem.add_hyperparameter([str(self.output_dir)], "output_dir")
        self.problem.add_hyperparameter(
            [self.simulator_config["compute_service_scheme"]], "compute_service_scheme")
        self.problem.add_hyperparameter(
            [self.simulator_config["storage_service_scheme"]], "storage_service_scheme")

        self.problem.add_hyperparameter(
            (MIN_REF_FLOPS, MAX_REF_FLOPS, SAMPLING), "reference_flops")
        self.problem.add_hyperparameter(
            (MIN_SCHED_OVER, MAX_SCHED_OVER, SAMPLING), "scheduling_overhead")

    def add_platform_parameters(self):
        self.problem.add_hyperparameter([True], "calib_platform")

        self.problem.add_hyperparameter(
            (MIN_PROC_SPEED, MAX_PROC_SPEED, SAMPLING),
            "speed")
        self.problem.add_hyperparameter(
            (MIN_BANDWIDTH, MAX_BANDWIDTH, SAMPLING),
            "bandwidth")
        self.problem.add_hyperparameter(
            (MIN_LATENCY, MAX_LATENCY, SAMPLING),
            "latency")
        self.problem.add_hyperparameter(
            (MIN_DISK_IO, MAX_DISK_IO, SAMPLING),
            "read_bw")
        self.problem.add_hyperparameter(
            (MIN_DISK_IO, MAX_DISK_IO, SAMPLING),
            "write_bw")

    def add_payloads_parameters(self):
        self.problem.add_hyperparameter([True], "calib_payloads")
        # Payload messages (discrete variables)
        possible_keys = ["compute_service_message_payloads",
                         "storage_service_message_payloads"]
        for key in possible_keys:
            if key in self.simulator_config:
                for service in self.simulator_config[key]:
                    for payloads in self.simulator_config[key][service]:
                        self.problem.add_hyperparameter(
                            (MIN_PAYLOADS_VAL, MAX_PAYLOADS_VAL, SAMPLING), key+"::"+service+"::"+payloads)

    def add_properties_parameters(self):
        # Properties (categorical variables)
        self.problem.add_hyperparameter([True], "calib_properties")

        possible_keys = ["compute_service_properties",
                         "storage_service_properties"]
        for key in possible_keys:
            if key in self.simulator_config:
                for service in self.simulator_config[key]:
                    for property in self.simulator_config[key][service]:
                        if property == "BATCH_SCHEDULING_ALGORITHM":
                            self.problem.add_hyperparameter(SCHEDULING_ALGO, key+"::"+service+"::"+property)
                        # elif property == "TASK_SELECTION_ALGORITHM":
                        #     self.problem.add_hyperparameter(TASK_SELECTION_ALGORITHM, key+"::"+service+"::"+property)
                        elif property == "BUFFER_SIZE":
                            # Model the concurrent access/buffer size with two variables:
                            # - inf or not inf
                            #   - if not inf we pick a discrete value between MIN and MAX
                            buffer_size_categorical = CSH.CategoricalHyperparameter(
                                "BUFFER_SIZE_CAT", choices=["infinity", "finite"])
                            # Express as power of 2^x : if range goes to 8 to 10 then the values will range from 2^8 to 2^10
                            buffer_size_discrete = CSH.UniformIntegerHyperparameter(
                                key+"::"+service+"::"+property, lower=20, upper=30, log=False)
                            self.problem.add_hyperparameter(buffer_size_categorical)
                            self.problem.add_hyperparameter(buffer_size_discrete)
                            # If we choose "finite" then we sample a discrete value for the buffer size
                            self.problem.add_condition(CS.EqualsCondition(
                                buffer_size_discrete, buffer_size_categorical, "finite"))
                        elif property == "MAX_NUM_CONCURRENT_DATA_CONNECTIONS":
                            conc_conn_categorical = CSH.CategoricalHyperparameter(
                                "MAX_NUM_CONCURRENT_CAT", choices=["infinity", "finite"])
                            conc_conn_discrete = CSH.UniformIntegerHyperparameter(
                                key+"::"+service+"::"+property, lower=1, upper=64, log=False)
                            self.problem.add_hyperparameter(conc_conn_categorical)
                            self.problem.add_hyperparameter(conc_conn_discrete)
                            self.problem.add_condition(CS.EqualsCondition(
                                conc_conn_discrete, conc_conn_categorical, "finite"))

    """
        Test the simulator to make sure it exists and that's a valid WRENCH simulator
    """

    def _test_simulator(self) -> Tuple[bool, str]:
        cmd = [self.simulator, "--version"]
        try:
            test_simu = subprocess.run(
                cmd, capture_output=True, text=True, check=True
            )
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            return (False, e)
        else:
            return (True, test_simu.stdout)

    """
        Load the JSON file that define the experiments
    """

    def _load_json(self, path: pathlib.Path) -> JSON:
        with open(path, 'r') as stream:
            return json.load(stream)

    """
        Write a dict in a JSON file
    """

    def write_json(self, data: JSON, path: pathlib.Path) -> None:
        with open(path, 'w') as f:
            json_data = json.dumps(data, indent=4)
            f.write(json_data)

    """
        Get CSV Header.
    """

    def _get_header(self, config: JSON) -> Tuple[bool, str]:

        config_path = pathlib.Path(f"header.json").resolve()

        # We first have to write a temp JSON
        with open(config_path, 'w') as temp_config:
            json_config = json.dumps(config, indent=4)
            temp_config.write(json_config)

        try:
            simulation = subprocess.run(
                [self.simulator, "--config", str(config_path), "--csv-header"],
                capture_output=True, text=True, check=True
            )
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            self.logger.error(f"{e}")
            return (False, e)
        else:
            return (True, simulation.stdout)
        finally:
            try:
                os.remove(config_path)
            except OSError as e:
                self.logger.error(f"{e}")
                return (False, e)

    """
        Launch the search.
    """

    def launch(self) -> pd.DataFrame:
        self.df = self.search.search(max_evals=self.max_evals, timeout=self.timeout)

        # Clean the dataframe and re-ordering the columns
        self.df["platform"] = self.df.apply(lambda row: pathlib.Path(
            pathlib.Path(row["platform"]).name).stem, axis=1)
        self.df["workflow"] = self.df.apply(lambda row: pathlib.Path(
            pathlib.Path(row["workflow"]).name).stem, axis=1)

        self.df = self.df.drop(self.df.filter(
            regex='BUFFER_SIZE_CAT|MAX_NUM_CONCURRENT_CAT|container|simulator|calib_platform|calib_properties|calib_payloads').columns, axis=1)

        cols = self.df.columns.tolist()

        # if self.consider_payloads:
        #     cols = cols[-4:] + cols[:-4]
        # elif self.consider_properties:
        #     self.df["wrench::SimpleStorageServiceProperty::BUFFER_SIZE"] = self.df["wrench::SimpleStorageServiceProperty::BUFFER_SIZE"].fillna(
        #         "infinity")
        #     self.df["wrench::SimpleStorageServiceProperty::MAX_NUM_CONCURRENT_DATA_CONNECTIONS"] = self.df["wrench::SimpleStorageServiceProperty::MAX_NUM_CONCURRENT_DATA_CONNECTIONS"].fillna(
        #         "infinity")
        #     cols = cols[-4:] + cols[:-4]
        # else:
        cols = cols[-4:] + cols[:-4]

        self.df = self.df[cols]
        self.write_csv()

        return self.df

    """
        Get the pandas data frame
    """

    def get_dataframe(self) -> pd.DataFrame | None:
        return self.df

    """
        Return the best payloads configurations found
    """

    def get_best_config(self) -> JSON:
        if self.df.empty:
            return None

        i_max = self.df.objective.argmax()
        best_config = {}
        best_config["wrench"] = {}
        best_config["property"] = {}

        for k, val in self.df.iloc[i_max].to_dict().items():
            l = k.split('::')
            if l[0] in ["platform", "workflow", "simulator", "container"]:
                best_config[l[0]] = str(val)
            elif l[0] == "wrench":
                if 'ServiceMessagePayload' in l[1]:
                    if l[1] not in best_config["wrench"]:
                        best_config["wrench"][l[1]] = {}
                    best_config["wrench"][l[1]][l[2]] = str(2**int(val))
                elif 'ServiceProperty' in l[1]:
                    if l[1] not in best_config["property"]:
                        best_config["property"][l[1]] = {}
                    if pd.isna(val) or val == "infinity":
                        best_config["property"][l[1]][l[2]] = "infinity"
                    elif 'BATCH_SCHEDULING_ALGORITHM' in l[2] or 'TASK_SELECTION_ALGORITHM' in l[2]:
                        best_config["property"][l[1]][l[2]] = val
                    else:
                        best_config["property"][l[1]][l[2]] = str(2**int(val))

        return best_config

    """
        Write the data frame into a CSV
    """

    def write_csv(self) -> None:
        if self.random_search:
            self.df.to_csv(self.output_dir+'/rs.csv', index=False)
        else:
            self.df.to_csv(self.output_dir+'/bo.csv', index=False)

    """
        Produce a figure of the error in function of the iteration
    """

    def plot(self, show: bool = False):
        plt.plot(self.df.objective,
                 label='Objective',
                 marker='o',
                 color="blue",
                 lw=2)

        plt.grid(True)
        plt.xlabel("Iterations")
        plt.ylabel("Error")
        filename = "results.pdf"
        plt.savefig(f"{self.output_dir}/{filename}")
        if show:
            plt.show()


if __name__ == "__main__":
    logger = configure_logger(level=logging.INFO)

    parser = argparse.ArgumentParser(
        description='Calibrate a WRENCH simulator using DeepHyper.')
    parser.add_argument('--config', '-c', dest='conf', action='store',
                        type=pathlib.Path, required=True,
                        help='Path for the JSON configuration file')

    parser.add_argument('--iterations', '-i', dest='iter', action='store',
                        type=int, default=1,
                        help='Number of iterations for DeepHyper'
                        )

    parser.add_argument('--all', '-a', action='store_true',
                        help='Perform a benchmark by running the \
                            same auto-calibration procedure using Bayesian Optimization \
                            and Random Search'
                        )

    parser.add_argument('--properties', action='store_true',
                        help='Calibrate the simulator with properties.'
                        )

    parser.add_argument('--payloads', action='store_true',
                        help='Calibrate the simulator with payloads.'
                        )

    args = parser.parse_args()

    if not args.conf.exists():
        logger.error(f"Configuration file '{args.conf}' does not exist.")
        exit(1)
    if args.conf.is_dir():
        logger.error(f"Configuration file '{args.conf}' is a directory.")
        exit(1)


    # We use shorter UUID for clarity
    exp_id = "exp-"+str(uuid.uuid4()).split('-')[-1]

    try:
        os.mkdir(exp_id)
    except OSError as e:
        print(e)
        exit(1)

    # Copy the configuration used
    shutil.copyfile(args.conf, f"{exp_id}/setup.json")

    bayesian = Calibrator(
        config=args.conf,
        random_search=False,
        max_evals=args.iter,
        timeout=300,  # 5 min timeout
        consider_payloads=args.payloads,
        consider_properties=args.properties,
        output_dir=exp_id,
        logger=logger
    )

    bayesian.launch()
    # # bayesian.plot(show=False)
    df_bayesian = bayesian.get_dataframe()
    # # print(df_bayesian)
    # best_config = bayesian.get_best_config()
    # print(best_config)

    # bayesian.write_json(best_config, f"{exp_id}/best-bo.json")

    df = pd.DataFrame({
        'exp': exp_id,
        'id': df_bayesian["id"],
        'worklow': df_bayesian['workflow'][0],
        'err_bo': df_bayesian["objective"].abs()
    }
    )

    if args.all:
        baseline = Calibrator(
            config=args.conf,
            random_search=True,
            max_evals=args.iter,
            timeout=300,  # 5 min timeout
            consider_payloads=args.payloads,
            consider_properties=args.properties,
            output_dir=exp_id,
            logger=logger
        )

        baseline.launch()
        df_baseline = baseline.get_dataframe()
        # best_config = baseline.get_best_config()
        # baseline.write_json(best_config, f"{exp_id}/best-rs.json")

        df = pd.DataFrame({
            'exp': exp_id,
            'id': df_bayesian["id"],
            'worklow': df_bayesian['workflow'][0],
            'err_bo': df_bayesian["objective"].abs(),
            'err_rs': df_baseline["objective"].abs()
        }
        )

    print(f"================================================")
    print(f"=============== {exp_id} ===============")
    print(f"================================================")
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

    print(f"================================================")
