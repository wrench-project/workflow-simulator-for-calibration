#!/usr/bin/env python3
import argparse
import time
from glob import glob
from datetime import timedelta
from Util import *
from itertools import groupby

import json

def parse_command_line_arguments():
	epilog_string = ""

	parser = argparse.ArgumentParser(
		prog=sys.argv[0],
		description='Workflow simulator calibrator',
		epilog=epilog_string)


	parser.add_argument('-a ', '--simulator_args', type=str, metavar="<json args>", required=False,
						help='Json string of arguments to give to siumulator')
	parser.add_argument('-o', '--output', type=str, metavar="<output>",
						help='Output path for new workflow')
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

	return vars(parser.parse_args())

	



def main():
	# Parse command-line arguments
	args= parse_command_line_arguments()

	#print(base64.urlsafe_b64encode(hashlib.md5(str(set(args['training_set'])).encode()).digest()))

	#print(training)
	
	
	simulator = Simulator(args["compute_service_scheme"],
						  args["storage_service_scheme"],
						  args["network_topology_scheme"])

	result=simulator(args["simulator_args"])
	with open(json.loads(args["simulator_args"]["workflow"]), 'r')) as source_json:
		data = json.load(source_json)
		data["real_makespan"]=result["real_makespan"]
	with open(args["output"], 'w') as output_json:
		json.dump(data, output_json)

if __name__ == "__main__":
	main()
