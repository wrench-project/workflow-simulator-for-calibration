#!/usr/bin/env python3
import json
import os
from sklearn.metrics import mean_squared_error as sklearn_mean_squared_error
from pathlib import Path
from typing import List, Callable, Any
import simcal as sc
import Simulator


class CalibrationLossEvaluator:
    def __init__(self, simulator: Simulator, ground_truth: List[str], loss: Callable, sc_calibrator: sc.calibrator.Base):
        self.simulator = simulator
        self.ground_truth = ground_truth
        self.loss_function = loss
        self.sc_calibrator = sc_calibrator

    def __call__(self, calibration: Any):
        res = []
        print(calibration)
        # Run simulator for all known ground truth points
        for workflow in self.ground_truth:
            res.append(self.simulator((workflow, calibration, self.sc_calibrator)))
        return self.loss_function([x[0] for x in res], [x[1] for x in res])


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

    def compute_calibration(self):

        calibrator = sc.calibrators.Grid()

        if self.compute_service_scheme == "all_bare_metal":
            calibrator.add_param("compute_service_scheme_parameters", sc.parameters.Exponential(10, 40).
                                 format("%lff").set_metadata(["compute_service_scheme_parameters",
                                                          "all_bare_metal",
                                                          "compute_hosts",
                                                          "speed"]))

            calibrator.add_param("thread_startup_overhead", sc.parameters.Linear(0, 10).
                                 format("%lfs").set_metadata(["compute_service_scheme_parameters",
                                                          "all_bare_metal",
                                                          "properties",
                                                          "BareMetalComputeServiceProperty::THREAD_STARTUP_OVERHEAD"]))
        else:
            raise Exception(f"Compute service scheme '{self.compute_service_scheme}' not implemented yet")

        if self.storage_service_scheme == "submit_only":
            calibrator.add_param("disk_read_bandwidth", sc.parameters.Exponential(10, 40).
                                 format("%lfbps").set_metadata(["storage_service_scheme_parameters",
                                                            "submit_only",
                                                            "bandwidth_submit_disk_read"]))
            calibrator.add_param("disk_write_bandwidth", sc.parameters.Exponential(10, 40).
                                 format("%lfbps").set_metadata(["storage_service_scheme_parameters",
                                                            "submit_only",
                                                            "bandwidth_submit_disk_write"]))
        else:
            raise Exception(f"Storage service scheme '{self.storage_service_scheme}' not implemented yet")

        if self.network_topology_scheme == "one_link":
            calibrator.add_param("link_bandwidth", sc.parameters.Exponential(10, 40).
                                 format("%lfbps").set_metadata(["network_topology_scheme_parameters",
                                                            "one_link",
                                                            "bandwidth"]))
            calibrator.add_param("link_latency", sc.parameters.Linear(0, 0.01).
                                 format("%lfs").set_metadata(["network_topology_scheme_parameters",
                                                          "one_link",
                                                          "latency"]))
        else:
            raise Exception(f"Network topology scheme '{self.network_topology_scheme}' not implemented yet")

        coordinator = sc.coordinators.ThreadPool(pool_size=1)

        evaluator = CalibrationLossEvaluator(self.simulator, self.workflows, self.loss, calibrator)

        calibration, loss = calibrator.calibrate(evaluator, timelimit=600, coordinator=coordinator)
        return calibration, loss
