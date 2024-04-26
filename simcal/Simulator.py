"""
"""
import os.path
import sys
import time
from typing import Any

import simcal as sc
import json

template_json_input = {
    "workflow": {
        "file": "some file",
        "reference_flops": "100Mf"
    },
    "error_computation_scheme": "makespan",
    "error_computation_scheme_parameters": {
        "makespan": {
        }
    },

    "scheduling_overhead": "10ms",

    "compute_service_scheme": "all_bare_metal",
    "compute_service_scheme_parameters": {
        "all_bare_metal": {
            "submit_host": {
                "num_cores": "16",
                "speed": "12345Gf"
            },
            "compute_hosts": {
                "num_cores": "16",
                "speed": "1f"
            },
            "properties": {
                "BareMetalComputeServiceProperty::THREAD_STARTUP_OVERHEAD": "42s"
            },
            "payloads": {
                "ServiceMessagePayload::DAEMON_STOPPED_MESSAGE_PAYLOAD": "0",
                "ComputeServiceMessagePayload::IS_THERE_AT_LEAST_ONE_HOST_WITH_AVAILABLE_RESOURCES_ANSWER_MESSAGE_PAYLOAD": "0",
                "ComputeServiceMessagePayload::IS_THERE_AT_LEAST_ONE_HOST_WITH_AVAILABLE_RESOURCES_REQUEST_MESSAGE_PAYLOAD": "0",
                "ComputeServiceMessagePayload::PILOT_JOB_EXPIRED_MESSAGE_PAYLOAD": "0",
                "ComputeServiceMessagePayload::PILOT_JOB_STARTED_MESSAGE_PAYLOAD": "0",
                "ComputeServiceMessagePayload::RESOURCE_DESCRIPTION_ANSWER_MESSAGE_PAYLOAD": "0",
                "ComputeServiceMessagePayload::RESOURCE_DESCRIPTION_REQUEST_MESSAGE_PAYLOAD": "0",
                "ComputeServiceMessagePayload::STANDARD_JOB_DONE_MESSAGE_PAYLOAD": "0",
                "ComputeServiceMessagePayload::STANDARD_JOB_FAILED_MESSAGE_PAYLOAD": "0",
                "ServiceMessagePayload::STOP_DAEMON_MESSAGE_PAYLOAD": "0",
                "ComputeServiceMessagePayload::SUBMIT_PILOT_JOB_ANSWER_MESSAGE_PAYLOAD": "0",
                "ComputeServiceMessagePayload::SUBMIT_PILOT_JOB_REQUEST_MESSAGE_PAYLOAD": "0",
                "ComputeServiceMessagePayload::SUBMIT_STANDARD_JOB_ANSWER_MESSAGE_PAYLOAD": "0",
                "ComputeServiceMessagePayload::SUBMIT_STANDARD_JOB_REQUEST_MESSAGE_PAYLOAD": "0",
                "ComputeServiceMessagePayload::TERMINATE_PILOT_JOB_ANSWER_MESSAGE_PAYLOAD": "0",
                "ComputeServiceMessagePayload::TERMINATE_PILOT_JOB_REQUEST_MESSAGE_PAYLOAD": "0",
                "ComputeServiceMessagePayload::TERMINATE_STANDARD_JOB_ANSWER_MESSAGE_PAYLOAD": "0",
                "ComputeServiceMessagePayload::TERMINATE_STANDARD_JOB_REQUEST_MESSAGE_PAYLOAD": "0",
                "BareMetalComputeServiceMessagePayload::FLOP_RATE_ANSWER_MESSAGE_PAYLOAD": "0",
                "BareMetalComputeServiceMessagePayload::FLOP_RATE_REQUEST_MESSAGE_PAYLOAD": "0",
                "BareMetalComputeServiceMessagePayload::NOT_ENOUGH_CORES_MESSAGE_PAYLOAD": "0"
            }
        },
        "htcondor_bare_metal": {
            "submit_host": {
                "num_cores": "1231",
                "speed": "123Gf"
            },
            "compute_hosts":
            {
                "num_cores": "16",
                "speed": "423Gf"
            },
            "bare_metal_properties": {
                "BareMetalComputeServiceProperty::THREAD_STARTUP_OVERHEAD": "42s"
            },
            "bare_metal_payloads": {
                "ServiceMessagePayload::DAEMON_STOPPED_MESSAGE_PAYLOAD": "0",
                "BareMetalComputeServiceMessagePayload::IS_THERE_AT_LEAST_ONE_HOST_WITH_AVAILABLE_RESOURCES_ANSWER_MESSAGE_PAYLOAD": "0",
                "BareMetalComputeServiceMessagePayload::IS_THERE_AT_LEAST_ONE_HOST_WITH_AVAILABLE_RESOURCES_REQUEST_MESSAGE_PAYLOAD": "0",
                "ComputeServiceMessagePayload::PILOT_JOB_EXPIRED_MESSAGE_PAYLOAD": "0",
                "ComputeServiceMessagePayload::PILOT_JOB_STARTED_MESSAGE_PAYLOAD": "0",
                "ComputeServiceMessagePayload::RESOURCE_DESCRIPTION_ANSWER_MESSAGE_PAYLOAD": "0",
                "ComputeServiceMessagePayload::RESOURCE_DESCRIPTION_REQUEST_MESSAGE_PAYLOAD": "0",
                "ComputeServiceMessagePayload::STANDARD_JOB_DONE_MESSAGE_PAYLOAD": "0",
                "ComputeServiceMessagePayload::STANDARD_JOB_FAILED_MESSAGE_PAYLOAD": "0",
                "ServiceMessagePayload::STOP_DAEMON_MESSAGE_PAYLOAD": "0",
                "ComputeServiceMessagePayload::SUBMIT_PILOT_JOB_ANSWER_MESSAGE_PAYLOAD": "0",
                "ComputeServiceMessagePayload::SUBMIT_PILOT_JOB_REQUEST_MESSAGE_PAYLOAD": "0",
                "ComputeServiceMessagePayload::SUBMIT_STANDARD_JOB_ANSWER_MESSAGE_PAYLOAD": "0",
                "ComputeServiceMessagePayload::SUBMIT_STANDARD_JOB_REQUEST_MESSAGE_PAYLOAD": "0",
                "BareMetalComputeServiceMessagePayload::TERMINATE_PILOT_JOB_ANSWER_MESSAGE_PAYLOAD": "0",
                "BareMetalComputeServiceMessagePayload::TERMINATE_PILOT_JOB_REQUEST_MESSAGE_PAYLOAD": "0",
                "BareMetalComputeServiceMessagePayload::TERMINATE_STANDARD_JOB_ANSWER_MESSAGE_PAYLOAD": "0",
                "BareMetalComputeServiceMessagePayload::TERMINATE_STANDARD_JOB_REQUEST_MESSAGE_PAYLOAD": "0",
                "BareMetalComputeServiceMessagePayload::FLOP_RATE_ANSWER_MESSAGE_PAYLOAD": "0",
                "BareMetalComputeServiceMessagePayload::FLOP_RATE_REQUEST_MESSAGE_PAYLOAD": "0",
                "BareMetalComputeServiceMessagePayload::NOT_ENOUGH_CORES_MESSAGE_PAYLOAD": "0"
            },
            "htcondor_properties": {
                "HTCondorComputeServiceProperty::NEGOTIATOR_OVERHEAD": "1.0ms",
                "HTCondorComputeServiceProperty::GRID_PRE_EXECUTION_DELAY": "10.0s",
                "HTCondorComputeServiceProperty::GRID_POST_EXECUTION_DELAY": "10.0"
            },
            "htcondor_payloads": {
                "ServiceMessagePayload::DAEMON_STOPPED_MESSAGE_PAYLOAD": "0",
                "HTCondorComputeServiceMessagePayload::IS_THERE_AT_LEAST_ONE_HOST_WITH_AVAILABLE_RESOURCES_ANSWER_MESSAGE_PAYLOAD": "0",
                "HTCondorComputeServiceMessagePayload::IS_THERE_AT_LEAST_ONE_HOST_WITH_AVAILABLE_RESOURCES_REQUEST_MESSAGE_PAYLOAD": "0",
                "ComputeServiceMessagePayload::PILOT_JOB_EXPIRED_MESSAGE_PAYLOAD": "0",
                "ComputeServiceMessagePayload::PILOT_JOB_STARTED_MESSAGE_PAYLOAD": "0",
                "ComputeServiceMessagePayload::RESOURCE_DESCRIPTION_ANSWER_MESSAGE_PAYLOAD": "0",
                "ComputeServiceMessagePayload::RESOURCE_DESCRIPTION_REQUEST_MESSAGE_PAYLOAD": "0",
                "ComputeServiceMessagePayload::STANDARD_JOB_DONE_MESSAGE_PAYLOAD": "0",
                "ComputeServiceMessagePayload::STANDARD_JOB_FAILED_MESSAGE_PAYLOAD": "0",
                "ServiceMessagePayload::STOP_DAEMON_MESSAGE_PAYLOAD": "0",
                "ComputeServiceMessagePayload::SUBMIT_PILOT_JOB_ANSWER_MESSAGE_PAYLOAD": "0",
                "ComputeServiceMessagePayload::SUBMIT_PILOT_JOB_REQUEST_MESSAGE_PAYLOAD": "0",
                "ComputeServiceMessagePayload::SUBMIT_STANDARD_JOB_ANSWER_MESSAGE_PAYLOAD": "0",
                "ComputeServiceMessagePayload::SUBMIT_STANDARD_JOB_REQUEST_MESSAGE_PAYLOAD": "0",
                "ComputeServiceMessagePayload::TERMINATE_PILOT_JOB_ANSWER_MESSAGE_PAYLOAD": "0",
                "ComputeServiceMessagePayload::TERMINATE_PILOT_JOB_REQUEST_MESSAGE_PAYLOAD": "0",
                "ComputeServiceMessagePayload::TERMINATE_STANDARD_JOB_ANSWER_MESSAGE_PAYLOAD": "0",
                "ComputeServiceMessagePayload::TERMINATE_STANDARD_JOB_REQUEST_MESSAGE_PAYLOAD": "0",
                "HTCondorComputeServiceMessagePayload::FLOP_RATE_ANSWER_MESSAGE_PAYLOAD": "0",
                "HTCondorComputeServiceMessagePayload::FLOP_RATE_REQUEST_MESSAGE_PAYLOAD": "0",
                "HTCondorComputeServiceMessagePayload::NOT_ENOUGH_CORES_MESSAGE_PAYLOAD": "0"
             }
        }
    },

    "storage_service_scheme": "submit_only",
    "storage_service_scheme_parameters": {
        "submit_only": {
            "bandwidth_submit_disk_read": "10000MBps",
            "bandwidth_submit_disk_write": "10000MBps",
            "submit_properties": {
                "StorageServiceProperty::BUFFER_SIZE": "42MB",
                "SimpleStorageServiceProperty::MAX_NUM_CONCURRENT_DATA_CONNECTIONS": "8"
            },
            "submit_payloads": {
                "ServiceMessagePayload::DAEMON_STOPPED_MESSAGE_PAYLOAD": "0",
                "StorageServiceMessagePayload::FILE_COPY_ANSWER_MESSAGE_PAYLOAD": "0",
                "StorageServiceMessagePayload::FILE_COPY_REQUEST_MESSAGE_PAYLOAD": "0",
                "StorageServiceMessagePayload::FILE_DELETE_ANSWER_MESSAGE_PAYLOAD": "0",
                "StorageServiceMessagePayload::FILE_DELETE_REQUEST_MESSAGE_PAYLOAD": "0",
                "StorageServiceMessagePayload::FILE_LOOKUP_ANSWER_MESSAGE_PAYLOAD": "0",
                "StorageServiceMessagePayload::FILE_LOOKUP_REQUEST_MESSAGE_PAYLOAD": "0",
                "StorageServiceMessagePayload::FILE_READ_ANSWER_MESSAGE_PAYLOAD": "0",
                "StorageServiceMessagePayload::FILE_READ_REQUEST_MESSAGE_PAYLOAD": "0",
                "StorageServiceMessagePayload::FILE_WRITE_ANSWER_MESSAGE_PAYLOAD": "0",
                "StorageServiceMessagePayload::FILE_WRITE_REQUEST_MESSAGE_PAYLOAD": "0",
                "StorageServiceMessagePayload::FREE_SPACE_ANSWER_MESSAGE_PAYLOAD": "0",
                "StorageServiceMessagePayload::FREE_SPACE_REQUEST_MESSAGE_PAYLOAD": "0",
                "ServiceMessagePayload::STOP_DAEMON_MESSAGE_PAYLOAD": "0"
            }
        },
        "submit_and_compute_hosts": {
            "bandwidth_submit_disk_read": "100MBps",
            "bandwidth_submit_disk_write": "10MBps",
            "submit_properties": {
                "StorageServiceProperty::BUFFER_SIZE": "42000000",
                "SimpleStorageServiceProperty::MAX_NUM_CONCURRENT_DATA_CONNECTIONS": "8"
            },
            "submit_payloads": {
                "ServiceMessagePayload::DAEMON_STOPPED_MESSAGE_PAYLOAD": "0",
                "StorageServiceMessagePayload::FILE_COPY_ANSWER_MESSAGE_PAYLOAD": "0",
                "StorageServiceMessagePayload::FILE_COPY_REQUEST_MESSAGE_PAYLOAD": "0",
                "StorageServiceMessagePayload::FILE_DELETE_ANSWER_MESSAGE_PAYLOAD": "0",
                "StorageServiceMessagePayload::FILE_DELETE_REQUEST_MESSAGE_PAYLOAD": "0",
                "StorageServiceMessagePayload::FILE_LOOKUP_ANSWER_MESSAGE_PAYLOAD": "0",
                "StorageServiceMessagePayload::FILE_LOOKUP_REQUEST_MESSAGE_PAYLOAD": "0",
                "StorageServiceMessagePayload::FILE_READ_ANSWER_MESSAGE_PAYLOAD": "0",
                "StorageServiceMessagePayload::FILE_READ_REQUEST_MESSAGE_PAYLOAD": "0",
                "StorageServiceMessagePayload::FILE_WRITE_ANSWER_MESSAGE_PAYLOAD": "0",
                "StorageServiceMessagePayload::FILE_WRITE_REQUEST_MESSAGE_PAYLOAD": "0",
                "StorageServiceMessagePayload::FREE_SPACE_ANSWER_MESSAGE_PAYLOAD": "0",
                "StorageServiceMessagePayload::FREE_SPACE_REQUEST_MESSAGE_PAYLOAD": "0",
                "ServiceMessagePayload::STOP_DAEMON_MESSAGE_PAYLOAD": "0"
            },
            "bandwidth_compute_host_disk_read": "100MBps",
            "bandwidth_compute_host_write": "10MBps",
            "compute_host_properties": {
                "StorageServiceProperty::BUFFER_SIZE": "1048576B",
                "SimpleStorageServiceProperty::MAX_NUM_CONCURRENT_DATA_CONNECTIONS": "8"
            },
            "compute_host_payloads": {
                "ServiceMessagePayload::DAEMON_STOPPED_MESSAGE_PAYLOAD": "0",
                "StorageServiceMessagePayload::FILE_COPY_ANSWER_MESSAGE_PAYLOAD": "0",
                "StorageServiceMessagePayload::FILE_COPY_REQUEST_MESSAGE_PAYLOAD": "0",
                "StorageServiceMessagePayload::FILE_DELETE_ANSWER_MESSAGE_PAYLOAD": "0",
                "StorageServiceMessagePayload::FILE_DELETE_REQUEST_MESSAGE_PAYLOAD": "0",
                "StorageServiceMessagePayload::FILE_LOOKUP_ANSWER_MESSAGE_PAYLOAD": "0",
                "StorageServiceMessagePayload::FILE_LOOKUP_REQUEST_MESSAGE_PAYLOAD": "0",
                "StorageServiceMessagePayload::FILE_READ_ANSWER_MESSAGE_PAYLOAD": "0",
                "StorageServiceMessagePayload::FILE_READ_REQUEST_MESSAGE_PAYLOAD": "0",
                "StorageServiceMessagePayload::FILE_WRITE_ANSWER_MESSAGE_PAYLOAD": "0",
                "StorageServiceMessagePayload::FILE_WRITE_REQUEST_MESSAGE_PAYLOAD": "0",
                "StorageServiceMessagePayload::FREE_SPACE_ANSWER_MESSAGE_PAYLOAD": "0",
                "StorageServiceMessagePayload::FREE_SPACE_REQUEST_MESSAGE_PAYLOAD": "0",
                "ServiceMessagePayload::STOP_DAEMON_MESSAGE_PAYLOAD": "0"
            }
        }
    },

    "network_topology_scheme": "many_links",
    "network_topology_scheme_parameters": {
        "one_link": {
            "bandwidth": "4MBps",
            "latency": "10us"
        },
        "one_and_then_many_links": {
            "bandwidth_out_of_submit": "4MBps",
            "latency_out_of_submit": "10us",
            "bandwidth_to_compute_hosts": "4MBps",
            "latency_to_compute_hosts": "10us"
        },
        "many_linksmany_links": {
            "bandwidth_submit_to_compute_host": "4000MBps",
            "latency_submit_to_compute_host": "10us"
        }
    }
}


class Simulator(sc.Simulator):

    def __init__(self):
        super().__init__()

    def run(self, env: sc.Environment, args: tuple[str, dict[str, sc.parameters.value]]) -> Any:
        (workflow, calibration) = args
        # Create the input json
        json_input = template_json_input.copy()
        # override the workflow
        json_input["workflow"]["file"] = workflow

        print("Running simulator")
        # override all parameter values
        for parameter in calibration:
            metadata = calibration[parameter].get_parameter().get_custom_data()
            tmp_object = json_input
            for item in metadata[0:-1]:
                tmp_object = tmp_object[item]
            tmp_object[metadata[-1]] = calibration[parameter]

        print("Running simulator 2")
        # Save the input json as a file
        print("Getting a temp directory\n")
        print(os.path.curdir)
        env.tmp_dir(directory=".", keep=False)
        print("Got a temp directory")
        print("Getting a temp file")
        json_file = env.tmp_file(directory=env.get_cwd(), encoding='utf8', keep=False)
        print("Got a temp file")
        print(json_input)
        json.dump(json_input, json_file, default=lambda o: str(o))
        json_file.flush()

        print("Running simulator 3")
        # Run the simulator
        cmdargs = [json_file.name]
        # print(" ".join(["workflow-simulator-for-calibration"] + cmdargs))
        print("workflow-simulator-for-calibration", cmdargs)
        std_out, std_err, exit_code = env.bash("workflow-simulator-for-calibration", cmdargs, std_in=None)
        if exit_code:
            sys.stderr.write(f"Simulator has failed with exit code {exit_code}!\n\n{std_err}\n")
            exit(1)
        # if std_err:
        #     print(std_out, std_err, exit_code)
        #     exit(1)
        print("Ran simulator")


        [simulated_makespan, real_makespan, error] = std_out.split(":")
        return float(simulated_makespan), float(real_makespan)
