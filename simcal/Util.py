import sys
import pickle
from typing import List, Callable

import simcal as sc

from Simulator import Simulator

from WorkflowSimulatorCalibrator import WorkflowSimulatorCalibrator


def relative_average_error(x: List[float], y: List[float]):
    return sum([abs(a - b) / a for (a, b) in list(zip(x, y))]) / len(x)


def _get_loss_function(loss_spec: str) -> Callable:
    if loss_spec == "mean_square_error":
        from sklearn.metrics import mean_squared_error as sklearn_mean_squared_error
        return sklearn_mean_squared_error
    elif loss_spec == "relative_average_error":
        return relative_average_error
    else:
        raise Exception(f"Unknown loss function name '{loss_spec}'")


def load_pickled_calibration(filepath: str,
                             compute_service_scheme: str,
                             storage_service_scheme: str,
                             network_topology_scheme: str):
    with open(filepath, 'rb') as file:
        pickled_calibration = pickle.load(file)
        calibration = pickled_calibration["calibration"]

        # Consistency checking
        if pickled_calibration["compute_service_scheme"] != compute_service_scheme:
            sys.stderr.write(f"Loading calibration's compute service scheme ("
                             f"{pickled_calibration['compute_service_scheme']}) "
                             f"inconsistent with command-line arguments ({compute_service_scheme})")
        if pickled_calibration["storage_service_scheme"] != storage_service_scheme:
            sys.stderr.write(f"Loading calibration's storage service scheme ("
                             f"{pickled_calibration['storage_service_scheme']}) "
                             f"inconsistent with command-line arguments ({storage_service_scheme})")
        if pickled_calibration["network_topology_scheme"] != network_topology_scheme:
            sys.stderr.write(f"Loading calibration's' network topology scheme ("
                             f"{pickled_calibration['network_topology_scheme']}) "
                             f"inconsistent with command-line arguments ({network_topology_scheme})")

        return pickled_calibration["calibration"], pickled_calibration["loss"]


def save_pickled_calibration(filepath: str,
                             calibration: dict[str, sc.parameters.Value],
                             loss: float,
                             compute_service_scheme: str,
                             storage_service_scheme: str,
                             network_topology_scheme: str):
    to_pickle = {"calibration": calibration,
                 "loss": loss,
                 "compute_service_scheme": compute_service_scheme,
                 "storage_service_scheme": storage_service_scheme,
                 "network_topology_scheme": network_topology_scheme}
    # Save it
    with open(filepath, 'wb') as f:
        pickle.dump(to_pickle, f)


def compute_calibration(workflows: List[str],
                        algorithm: str,
                        simulator: Simulator,
                        compute_service_scheme: str,
                        storage_service_scheme: str,
                        network_topology_scheme: str,
                        loss_spec: str,
                        time_limit: float, num_threads: int):

    calibrator = WorkflowSimulatorCalibrator(workflows,
                                             algorithm,
                                             simulator,
                                             compute_service_scheme,
                                             storage_service_scheme,
                                             network_topology_scheme,
                                             _get_loss_function(loss_spec))

    calibration, loss = calibrator.compute_calibration(time_limit, num_threads)
    return calibration, loss


def evaluate_calibration(workflows: List[str],
                         simulator: Simulator,
                         calibration: dict[str, sc.parameters.Value],
                         loss_spec: str) -> float:
    results = []
    for workflow in workflows:
        res = simulator((workflow, calibration))
        results.append(res)
    simulated_makespans, real_makespans = zip(*results)
    return _get_loss_function(loss_spec)(simulated_makespans, real_makespans)
