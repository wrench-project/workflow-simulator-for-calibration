import json
import os
import sys
from time import time

import simcal
from sklearn.metrics import mean_squared_error as sklearn_mean_squared_error
from pathlib import Path
from typing import List, Callable, Any
import simcal as sc
import Simulator


class CalibrationLossEvaluator:
    def __init__(self, simulator: Simulator, ground_truth: List[str], loss: Callable):
        self.simulator = simulator
        self.ground_truth = ground_truth
        self.loss_function = loss

    def __call__(self, calibration: Any, stop_time: float):
        results = []
        # Run simulator for all known ground truth points
        for workflow in self.ground_truth:
            results.append(self.simulator((workflow, calibration), stoptime=stop_time))
        simulated_makespans, real_makespans = zip(*results)
        return self.loss_function(simulated_makespans, real_makespans)


class WorkflowSimulatorCalibrator:
    def __init__(self, workflows: List[str],
                 algorithm: str,
                 simulator: Simulator,

                 loss: Callable):
        self.workflows = workflows
        self.algorithm = algorithm
        self.simulator = simulator
        self.loss = loss

    def compute_calibration(self, time_limit: float, num_threads: int):

        if self.algorithm == "grid":
            calibrator = sc.calibrators.Grid()
        elif self.algorithm == "random":
            calibrator = sc.calibrators.Random()
        elif self.algorithm == "gradient":
            calibrator = sc.calibrators.GradientDescent(0.001, 0.00001)
        else:
            raise Exception(f"Unknown calibration algorithm {self.algorithm}")

        # COMPUTE SERVICE SCHEME
        if self.simulator.compute_service_scheme == "all_bare_metal":
            calibrator.add_param("compute_hosts_speed", sc.parameters.Exponential(10, 40).
                                 format("%lff").set_custom_data(["compute_service_scheme_parameters",
                                                                 "all_bare_metal",
                                                                 "compute_hosts",
                                                                 "speed"]))

            calibrator.add_param("thread_startup_overhead", sc.parameters.Linear(0, 10).
                                 format("%lfs").set_custom_data(["compute_service_scheme_parameters",
                                                                 "all_bare_metal",
                                                                 "properties",
                                                                 "BareMetalComputeServiceProperty::THREAD_STARTUP_OVERHEAD"]))

        elif self.simulator.compute_service_scheme == "htcondor_bare_metal":
            calibrator.add_param("compute_hosts_speed", sc.parameters.Exponential(10, 40).
                                 format("%lff").set_custom_data(["compute_service_scheme_parameters",
                                                                 "htcondor_bare_metal",
                                                                 "compute_hosts",
                                                                 "speed"]))

            calibrator.add_param("thread_startup_overhead", sc.parameters.Linear(0, 10).
                                 format("%lfs").set_custom_data(["compute_service_scheme_parameters",
                                                                 "htcondor_bare_metal",
                                                                 "bare_metal_properties",
                                                                 "BareMetalComputeServiceProperty::THREAD_STARTUP_OVERHEAD"]))

            calibrator.add_param("htcondor_negotiator_overhead", sc.parameters.Linear(0, 10).
                                 format("%lfs").set_custom_data(["compute_service_scheme_parameters",
                                                                 "htcondor_bare_metal",
                                                                 "htcondor_properties",
                                                                 "HTCondorComputeServiceProperty::NEGOTIATOR_OVERHEAD"]))

            calibrator.add_param("htcondor_pre_execution_delay", sc.parameters.Linear(0, 10).
                                 format("%lfs").set_custom_data(["compute_service_scheme_parameters",
                                                                 "htcondor_bare_metal",
                                                                 "htcondor_properties",
                                                                 "HTCondorComputeServiceProperty::GRID_PRE_EXECUTION_DELAY"]))

            calibrator.add_param("htcondor_post_execution_delay", sc.parameters.Linear(0, 10).
                                 format("%lfs").set_custom_data(["compute_service_scheme_parameters",
                                                                 "htcondor_bare_metal",
                                                                 "htcondor_properties",
                                                                 "HTCondorComputeServiceProperty::GRID_POST_EXECUTION_DELAY"]))

        else:
            raise Exception(f"Compute service scheme '{self.simulator.compute_service_scheme}' not implemented yet")


        # STORAGE SERVICE SCHEME
        if self.simulator.storage_service_scheme == "submit_only":
            calibrator.add_param("disk_read_bw", sc.parameters.Exponential(10, 40).
                                 format("%lfbps").set_custom_data(["storage_service_scheme_parameters",
                                                                   "submit_only",
                                                                   "bandwidth_submit_disk_read"]))
            calibrator.add_param("disk_write_bw", sc.parameters.Exponential(10, 40).
                                 format("%lfbps").set_custom_data(["storage_service_scheme_parameters",
                                                                   "submit_only",
                                                                   "bandwidth_submit_disk_write"]))
            calibrator.add_param("max_num_data_connections", sc.parameters.Linear(0, 100).
                                 format("%d").set_custom_data(["storage_service_scheme_parameters",
                                                               "submit_only",
                                                               "submit_properties",
                                                               "SimpleStorageServiceProperty::MAX_NUM_CONCURRENT_DATA_CONNECTIONS"]))

        elif self.simulator.storage_service_scheme == "submit_and_compute_hosts":
            calibrator.add_param("submit_disk_read_bw", sc.parameters.Exponential(20, 40).
                                 format("%lfbps").set_custom_data(["storage_service_scheme_parameters",
                                                                   "submit_and_compute_hosts",
                                                                   "bandwidth_submit_disk_read"]))
            calibrator.add_param("submit_disk_write_bw", sc.parameters.Exponential(20, 40).
                                 format("%lfbps").set_custom_data(["storage_service_scheme_parameters",
                                                                   "submit_and_compute_hosts",
                                                                   "bandwidth_submit_disk_write"]))
            calibrator.add_param("submit_max_num_data_connections", sc.parameters.Linear(0, 100).
                                 format("%d").set_custom_data(["storage_service_scheme_parameters",
                                                               "submit_and_compute_hosts",
                                                               "submit_properties",
                                                               "SimpleStorageServiceProperty::MAX_NUM_CONCURRENT_DATA_CONNECTIONS"]))

            calibrator.add_param("compute_host_disk_read_bw", sc.parameters.Exponential(20, 40).
                                 format("%lfbps").set_custom_data(["storage_service_scheme_parameters",
                                                                   "submit_and_compute_hosts",
                                                                   "bandwidth_compute_host_disk_read"]))
            calibrator.add_param("compute_host_disk_write_bw", sc.parameters.Exponential(20, 40).
                                 format("%lfbps").set_custom_data(["storage_service_scheme_parameters",
                                                                   "submit_and_compute_hosts",
                                                                   "bandwidth_compute_host_write"]))
            calibrator.add_param("compute_host_max_num_data_connections", sc.parameters.Linear(0, 100).
                                 format("%d").set_custom_data(["storage_service_scheme_parameters",
                                                               "submit_and_compute_hosts",
                                                               "compute_host_properties",
                                                               "SimpleStorageServiceProperty::MAX_NUM_CONCURRENT_DATA_CONNECTIONS"]))
        else:
            raise Exception(f"Storage service scheme '{self.simulator.storage_service_scheme}' not implemented yet")

        # NETWORK TOPOLOGY SCHEME
        if self.simulator.network_topology_scheme == "one_link":
            calibrator.add_param("link_bw", sc.parameters.Exponential(10, 40).
                                 format("%lfbps").set_custom_data(["network_topology_scheme_parameters",
                                                                   "one_link",
                                                                   "bandwidth"]))
            calibrator.add_param("link_lat", sc.parameters.Linear(0, 0.01).
                                 format("%lfs").set_custom_data(["network_topology_scheme_parameters",
                                                                 "one_link",
                                                                 "latency"]))

        elif self.simulator.network_topology_scheme == "many_links":
            calibrator.add_param("link_bw", sc.parameters.Exponential(10, 40).
                                 format("%lfbps").set_custom_data(["network_topology_scheme_parameters",
                                                                   "many_links",
                                                                   "bandwidth_submit_to_compute_host"]))
            calibrator.add_param("link_lat", sc.parameters.Linear(0, 0.01).
                                 format("%lfs").set_custom_data(["network_topology_scheme_parameters",
                                                                 "many_links",
                                                                 "latency_submit_to_compute_host"]))

        elif self.simulator.network_topology_scheme == "one_and_then_many_links":
            calibrator.add_param("first_link_bw", sc.parameters.Exponential(10, 40).
                                 format("%lfbps").set_custom_data(["network_topology_scheme_parameters",
                                                                   "one_and_then_many_links",
                                                                   "bandwidth_out_of_submit"]))
            calibrator.add_param("first_link_lat", sc.parameters.Linear(0, 0.01).
                                 format("%lfs").set_custom_data(["network_topology_scheme_parameters",
                                                                 "one_and_then_many_links",
                                                                 "latency_out_of_submit"]))
            calibrator.add_param("second_link_bw", sc.parameters.Exponential(10, 40).
                                 format("%lfbps").set_custom_data(["network_topology_scheme_parameters",
                                                                   "one_and_then_many_links",
                                                                   "bandwidth_to_compute_hosts"]))
            calibrator.add_param("second_link_lat", sc.parameters.Linear(0, 0.01).
                                 format("%lfs").set_custom_data(["network_topology_scheme_parameters",
                                                                 "one_and_then_many_links",
                                                                 "latency_submit_to_compute_host"]))

        else:
            raise Exception(f"Network topology scheme '{self.simulator.network_topology_scheme}' not implemented yet")

        coordinator = sc.coordinators.ThreadPool(pool_size=num_threads)

        evaluator = CalibrationLossEvaluator(self.simulator, self.workflows, self.loss)

        calibration, loss = calibrator.calibrate(evaluator, timelimit=time_limit, coordinator=coordinator)

        return calibration, loss
