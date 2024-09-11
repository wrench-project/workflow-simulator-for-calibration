#!/usr/bin/env python3
import argparse
import time
from glob import glob
from datetime import timedelta
import math

from Util import *
from Util import _get_loss_function


def parse_command_line_arguments(program_name: str):
	epilog_string = ""

	parser = argparse.ArgumentParser(
		prog=program_name,
		description='Workflow simulator calibrator',
		epilog=epilog_string)

	try:

		parser.add_argument('-wd', '--workflow_dir', type=str, metavar="<workflow dir>", required=True,
							help='Directory that contains all workflow instances')
		#parser.add_argument('-cn', '--computer_name', type=str, metavar="<computer name>", required=True,
		#					help='Name of this computer to add to the pickled file name')
		parser.add_argument('-wn', '--workflow_name', type=str, metavar="<workflow name>", required=True,
							help='Name of the workflow to run the calibration/validation on')
		parser.add_argument('-ar', '--architecture', type=str,
							metavar="[haswell|skylake|cascadelake]",
							choices=['haswell', 'skylake', 'cascadelake'], required=True,
							help='The computer architecture')
		#parser.add_argument('-al', '--algorithm', type=str,
		#					metavar="[grid|random|gradient|skopt.gp|skopt.gbrt|]",
		#					choices=['grid', 'random', 'gradient','skopt.gp','skopt.gbrt'], required=True,
		#					help='The calibration algorithm')
		parser.add_argument('-tl', '--time_limit', type=int, metavar="<number of second>", required=True,
							help='A training time limit, in seconds')
		parser.add_argument('-th', '--num_threads', type=int, metavar="<number of threads (default=1)>", nargs='?',
							default=1, help='A number of threads to use for training')
		parser.add_argument('-n', '--estimate_run_time_only', action="store_true",
							help='A number of threads to use for training')
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
		parser.add_argument('-gd', '--delta', type=str,
							required=True,
							help='The range of orders of magnitude to use for gradient descent delta (shift) parameter')
		parser.add_argument('-ge', '--epsilon', type=str,
							required=True,
							help='The range of orders of magnitude to use for gradient descent epsilon (flat) parameter')
		return vars(parser.parse_args()), parser, None

	except argparse.ArgumentError as error:
		return None, parser, error


def main():
	# Parse command-line arguments
	args, parser, error = parse_command_line_arguments(sys.argv[0])
	if not args:
		sys.stderr.write(f"Error: {error}\n")
		parser.print_usage()
		sys.exit(1)

	# Pickle results filename
	#pickle_file_name = f"pickled-one_workflow_experiments-" \
	#				   f"{args['workflow_name']}-" \
	#				   f"{args['architecture']}-" \
	#				   f"{args['compute_service_scheme']}-" \
	#				   f"{args['storage_service_scheme']}-" \
	#				   f"{args['network_topology_scheme']}-" \
	#				   f"{args['algorithm']}-" \
	#				   f"{args['time_limit']}-" \
	#				   f"{args['num_threads']}-" \
	#				   f"{args['computer_name']}.pickled"

	# If the pickled file already exists, then print a warning and move on
	#if os.path.isfile(pickle_file_name):
	#	sys.stderr.write(f"There is already a pickled file '{pickle_file_name}'... Not doing anything!\n")
	#	sys.exit(1)

	# Build list of workflows
	search_string = f"{args['workflow_dir']}/" \
					f"{args['workflow_name']}-" \
					f"*-" \
					f"*-" \
					f"*-" \
					f"*-" \
					f"{args['architecture']}-" \
					f"*-*.json"

	workflows = glob(search_string)
	# workflows = [os.path.abspath(x) for x in workflows]  # Make all path absolute
	if len(workflows) == 0:
		sys.stdout.write(f"No workflow found ({search_string})\n")
		sys.exit(1)

	# Build lists of the characteristics for which we have data
	num_tasks_values = set({})
	cpu_values = set({})
	data_values = set({})
	num_nodes_values = set({})
	for workflow in workflows:
		tokens = workflow.split('/')[-1].split("-")
		num_tasks_values.add(int(tokens[1]))
		cpu_values.add(int(tokens[2]))
		data_values.add(int(tokens[4]))
		num_nodes_values.add(int(tokens[6]))
	num_tasks_values = sorted(list(num_tasks_values))
	cpu_values = sorted(list(cpu_values))
	data_values = sorted(list(data_values))
	num_nodes_values = sorted(list(num_nodes_values))

	sys.stderr.write(f"Found {len(workflows)} {args['workflow_name']} workflows to work with: \n")
	sys.stderr.write(f"  #tasks:		 {num_tasks_values}\n")
	sys.stderr.write(f"  cpu work:	   {cpu_values}\n")
	sys.stderr.write(f"  data footprint: {data_values}\n")
	sys.stderr.write(f"  #compute nodes: {num_nodes_values}\n\n")

	simulator = Simulator(args["compute_service_scheme"],
						  args["storage_service_scheme"],
						  args["network_topology_scheme"])

	sys.stderr.write("Creating experiments")
	# Num task variation experiments
	

	training=WorkflowSetSpec(args["workflow_dir"],
								args["workflow_name"],
								args["architecture"],
								num_tasks_values, data_values, cpu_values, 
								num_nodes_values)
				

	
	#time_estimate_str = timedelta(seconds=experiment_set.estimate_run_time())

	dh,dl=args["delta"].split(",")
	eh,el=args["epsilon"].split(",")
	dl=float(dl)
	el=float(el)
	dh=float(dh)
	eh=float(eh)
	calibrator = WorkflowSimulatorCalibrator(training.get_workflow_set(),
													 "gradient",
													 simulator,
													 _get_loss_function(args["loss_function"]))
	best_args=None
	bestLoss=None
	d=dh
	for i in range(int(math.ceil(abs(math.log10(dl)-math.log10(dh))))):
		e=eh
		for j in range(int(math.ceil(abs(math.log10(el)-math.log10(eh))))):
			
			calibrator.gradientDescentStep=d
			calibrator.gradientDescentFlat=e
			calibration, loss = calibrator.compute_calibration(args["time_limit"], args["num_threads"])
			if bestLoss is None or bestLoss>loss:
				best_args=(e,d)
				bestLoss=loss
			print((e,d))
			e/=10
		d/=10
	print(best_args,bestLoss)

if __name__ == "__main__":
	main()
