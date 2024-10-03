#!/usr/bin/env python3
import argparse
import time
from glob import glob
from datetime import timedelta
import base64
import sys
from Util import *
import hashlib

def parse_command_line_arguments(program_name: str):
	epilog_string = ""

	parser = argparse.ArgumentParser(
		prog=program_name,
		description='Workflow simulator calibrator',
		epilog=epilog_string)

	try:

		parser.add_argument('-wd', '--workflow_dir', type=str, metavar="<workflow dir>", required=True,
							help='Directory that contains all workflow instances')
		parser.add_argument('-cn', '--computer_name', type=str, metavar="<computer name>", required=True,
							help='Name of this computer to add to the pickled file name')
		#parser.add_argument('-wn', '--workflow_name', type=str, metavar="<workflow name>", required=True,
		#					help='Name of the workflow to run the calibration/validation on')
		#parser.add_argument('-ar', '--architecture', type=str,
		#					metavar="[haswell|skylake|cascadelake|icelake]",
		#					choices=['haswell', 'skylake', 'cascadelake','icelake'], required=True,
		#					help='The computer architecture')
		parser.add_argument('-al', '--algorithm', type=str,
							metavar="[grid|random|gradient|skopt.gp|skopt.gbrt|skopt.rf|skopt.et]",
							choices=['grid', 'random', 'gradient','skopt.gp','skopt.gbrt','skopt.rf','skopt.et'], required=True,
							help='The calibration algorithm')
		parser.add_argument('-tl', '--time_limit', type=int, metavar="<number of second>", required=True,
							help='A training time limit, in seconds')
		parser.add_argument('-th', '--num_threads', type=int, metavar="<number of threads (default=1)>", nargs='?',
							default=1, help='A number of threads to use for training')
		#parser.add_argument('-n', '--estimate_run_time_only', action="store_true",
		#					help='A number of threads to use for training')
		parser.add_argument('-lf', '--loss_function', type=str,
							metavar="mean_square_error, relative_average_error",
							choices=['mean_square_error', 'relative_average_error'], nargs='?',
							default="relative_average_error",
							help='The loss function to evaluate a calibration')
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
		parser.add_argument('-ts', '--training_set',required=True, type=str, nargs="+",
							help='The list of json files to use for training')
		parser.add_argument('-es', '--evaluation_set', type=str, nargs="*",default=(), 
							help='The list of json files to use for evaluation')
		return vars(parser.parse_args()), parser, None

	except argparse.ArgumentError as error:
		return None, parser, error

def orderinvarient_hash(x,l):
	acc=bytearray(hashlib.md5(bytes(len(x))).digest())
	for i in x:
		tmp=hashlib.md5(i.encode()).digest()
		
		for j in range(len(acc)):
			#acc[j]^=tmp[j]
			acc[j]=(tmp[j]+acc[j])%256
	return base64.urlsafe_b64encode(acc)[:l].decode()


def main():
	# Parse command-line arguments
	args, parser, error = parse_command_line_arguments(sys.argv[0])
	if not args:
		sys.stderr.write(f"Error: {error}\n")
		parser.print_usage()
		sys.exit(1)
	#print(base64.urlsafe_b64encode(hashlib.md5(str(set(args['training_set'])).encode()).digest()))
	# Pickle results filename
	pickle_file_name = f"pickled-one_workflow_experiments-" \
					   f"{orderinvarient_hash(args['training_set'],8)}-" \
					   f"{orderinvarient_hash(args['evaluation_set'],8)}-" \
					   f"{args['compute_service_scheme']}-" \
					   f"{args['storage_service_scheme']}-" \
					   f"{args['network_topology_scheme']}-" \
					   f"{args['algorithm']}-" \
					   f"{args['time_limit']}-" \
					   f"{args['num_threads']}-" \
					   f"{args['computer_name']}.pickled"

	# If the pickled file already exists, then print a warning and move on
	if os.path.isfile(pickle_file_name):
		sys.stderr.write(f"There is already a pickled file '{pickle_file_name}'... Not doing anything!\n")
		sys.exit(1)

	
	workflows = args['training_set']

	simulator = Simulator(args["compute_service_scheme"],
						  args["storage_service_scheme"],
						  args["network_topology_scheme"])

	experiment_set = ExperimentSet(simulator,
								   args["algorithm"],
								   args["loss_function"],
								   args["time_limit"],
								   args["num_threads"])

	num_tasks_values = []
	cpu_values = []
	data_values = []
	num_nodes_values = []
	for workflow in workflows:
		tokens = workflow.split('/')[-1].split("-")
		num_tasks_values.append(int(tokens[1]))
		cpu_values.append(int(tokens[2]))
		data_values.append(int(tokens[4]))
		num_nodes_values.append(int(tokens[6]))
	print(num_tasks_values)
	print(cpu_values )
	print(data_values )
	print(num_nodes_values)
	exit()
	experiment_set.add_experiment(
		WorkflowSetSpec(args["workflow_dir"],
						args["workflow_name"],
						args["architecture"],
						num_tasks_values[0:i], data_values, cpu_values, [num_nodes]),
		[
			WorkflowSetSpec(args["workflow_dir"],
							args["workflow_name"],
							args["architecture"],
							num_tasks_values[i:], data_values, cpu_values, [num_nodes]),
			WorkflowSetSpec(args["workflow_dir"],
							args["workflow_name"],
							args["architecture"],
							[num_tasks_values[-1]], data_values, cpu_values, [num_nodes]),
		])
		
	start = time.perf_counter()
	experiment_set.run()
	elapsed = int(time.perf_counter() - start)
	sys.stderr.write(f"Actually ran in {timedelta(seconds=elapsed)}\n")
	# except Exception as error:
	#	sys.stderr.write(str(type(error)))
	#	sys.stderr.write(f"Error while running experiments: {error}\n")
	#	sys.exit(1)
	# dont catch print exit errors.  Just let the error throw its self and python will give a much better print then still exit

	# Pickle it
	with open(pickle_file_name, 'wb') as f:
		pickle.dump(experiment_set, f)
	sys.stderr.write(f"Pickled to ./{pickle_file_name}\n")


if __name__ == "__main__":
	main()
