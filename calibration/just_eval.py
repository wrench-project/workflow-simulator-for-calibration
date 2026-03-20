#!/usr/bin/env python3
import argparse
import time
from glob import glob
from datetime import timedelta
from Util import *
from itertools import groupby
from statistics import mean

import json

def parse_command_line_arguments():
	epilog_string = ""

	parser = argparse.ArgumentParser(
		prog=sys.argv[0],
		description='Workflow simulator calibrator',
		epilog=epilog_string)


	parser.add_argument('-a ', '--simulator_args', type=str, metavar="<json args>", 
						help='Json string of arguments to give to siumulator')


	return vars(parser.parse_args())

	



def main():
	# Parse command-line arguments
	args= parse_command_line_arguments()

	#print(base64.urlsafe_b64encode(hashlib.md5(str(set(args['training_set'])).encode()).digest()))

	#print(training)
	
	
	sim_args=json.loads(args["simulator_args"])
	cmdargs = ["--wrench-commport-pool-size=10000",f"{args["simulator_args"]}"]
	std_out, std_err, exit_code = sc.bash("workflow-simulator-for-calibration", cmdargs, std_in=None)
	if std_err:
		print(std_err)
	
	result=json.loads(std_out)
	losses = []
	with open(sim_args["workflow"]["file"], 'r') as source_json:
		data = json.load(source_json)
		real_makespan = float(data["workflow"]["execution"]["makespanInSeconds"])
		simulated_makespan = float(result["simulated_makespan"])
	print( abs(real_makespan-simulated_makespan)/real_makespan)



if __name__ == "__main__":
	main()
# Calibration Used: '{"workflow":{"file":"'$file'","reference_flops":"100Mf"},"error_computation_scheme":"makespan","error_computation_scheme_parameters":{"makespan":{}},"scheduling_overhead":"10ms","compute_service_scheme":"htcondor_bare_metal","compute_service_scheme_parameters":{"all_bare_metal":{"submit_host":{"num_cores":"16","speed":"12345Gf"},"compute_hosts":{"num_cores":"16","speed":"1f"},"properties":{"BareMetalComputeServiceProperty::THREAD_STARTUP_OVERHEAD":"42s"},"payloads":{}},"htcondor_bare_metal":{"submit_host":{"num_cores":"1231","speed":"123Gf"},"compute_hosts":{"num_cores":"16","speed":"982452266.749154f"},"bare_metal_properties":{"BareMetalComputeServiceProperty::THREAD_STARTUP_OVERHEAD":"3.045662s"},"bare_metal_payloads":{},"htcondor_properties":{"HTCondorComputeServiceProperty::NEGOTIATOR_OVERHEAD":"12.338810s","HTCondorComputeServiceProperty::GRID_PRE_EXECUTION_DELAY":"14.790155s","HTCondorComputeServiceProperty::GRID_POST_EXECUTION_DELAY":"14.079311s"},"htcondor_payloads":{}}},"storage_service_scheme":"submit_and_compute_hosts","storage_service_scheme_parameters":{"submit_only":{"bandwidth_submit_disk_read":"10000MBps","bandwidth_submit_disk_write":"10000MBps","submit_properties":{"StorageServiceProperty::BUFFER_SIZE":"42MB","SimpleStorageServiceProperty::MAX_NUM_CONCURRENT_DATA_CONNECTIONS":"8"},"submit_payloads":{}},"submit_and_compute_hosts":{"bandwidth_submit_disk_read":"428823427550.539185bps","bandwidth_submit_disk_write":"4398215356.339356bps","submit_properties":{"StorageServiceProperty::BUFFER_SIZE":"42000000","SimpleStorageServiceProperty::MAX_NUM_CONCURRENT_DATA_CONNECTIONS":"59"},"submit_payloads":{},"bandwidth_compute_host_disk_read":"28687530839.627506bps","bandwidth_compute_host_write":"24561408103.754391bps","compute_host_properties":{"StorageServiceProperty::BUFFER_SIZE":"1048576B","SimpleStorageServiceProperty::MAX_NUM_CONCURRENT_DATA_CONNECTIONS":"28"},"compute_host_payloads":{}}},"network_topology_scheme":"one_and_then_many_links","network_topology_scheme_parameters":{"one_link":{"bandwidth":"4MBps","latency":"10us"},"many_links":{"bandwidth_submit_to_compute_host":"4000MBps","latency_submit_to_compute_host":"10us"},"one_and_then_many_links":{"bandwidth_out_of_submit":"16226331284.128448bps","latency_out_of_submit":"0.009044s","bandwidth_to_compute_hosts":"11195981534.552021bps","latency_to_compute_hosts":"10us","latency_submit_to_compute_host":"0.008494s"}}}'