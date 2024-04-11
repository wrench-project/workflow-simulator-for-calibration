import json
import os
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

    def __call__(self, calibration: Any):
        results = []
        # Run simulator for all known ground truth points
        for workflow in self.ground_truth:
            results.append(self.simulator((workflow, calibration)))

        simulated_makespans, real_makespans = zip(*results)
        return self.loss_function(simulated_makespans, real_makespans)


class WorkflowSimulatorCalibrator:
    def __init__(self, workflows: List[str],
                 simulator: Simulator,
                 compute_service_scheme,
                 storage_service_scheme,
                 network_topology_scheme,
                 loss: Callable):
        self.workflows = workflows
        self.simulator = simulator
        self.compute_service_scheme = compute_service_scheme
        self.storage_service_scheme = storage_service_scheme
        self.network_topology_scheme = network_topology_scheme
        self.loss = loss

    def compute_calibration(self, time_limit: float, num_threads: int):

        calibrator = sc.calibrators.Random()

        if self.compute_service_scheme == "all_bare_metal":
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
        else:
            raise Exception(f"Compute service scheme '{self.compute_service_scheme}' not implemented yet")

        if self.storage_service_scheme == "submit_only":
            calibrator.add_param("disk_read_bw", sc.parameters.Exponential(10, 40).
                                 format("%lfbps").set_custom_data(["storage_service_scheme_parameters",
                                                                   "submit_only",
                                                                   "bandwidth_submit_disk_read"]))
            calibrator.add_param("disk_write_bw", sc.parameters.Exponential(10, 40).
                                 format("%lfbps").set_custom_data(["storage_service_scheme_parameters",
                                                                   "submit_only",
                                                                   "bandwidth_submit_disk_write"]))
        else:
            raise Exception(f"Storage service scheme '{self.storage_service_scheme}' not implemented yet")

        if self.network_topology_scheme == "one_link":
            calibrator.add_param("link_bw", sc.parameters.Exponential(10, 40).
                                 format("%lfbps").set_custom_data(["network_topology_scheme_parameters",
                                                                   "one_link",
                                                                   "bandwidth"]))
            calibrator.add_param("link_lat", sc.parameters.Linear(0, 0.01).
                                 format("%lfs").set_custom_data(["network_topology_scheme_parameters",
                                                                 "one_link",
                                                                 "latency"]))
        else:
            raise Exception(f"Network topology scheme '{self.network_topology_scheme}' not implemented yet")

        coordinator = sc.coordinators.ThreadPool(pool_size=num_threads)

        evaluator = CalibrationLossEvaluator(self.simulator, self.workflows, self.loss)

        calibration, loss = calibrator.calibrate(evaluator, timelimit=time_limit, coordinator=coordinator)

        return calibration, loss
