#!/usr/bin/env python3
import argparse
import time
from glob import glob
from datetime import timedelta
from Util import *
from itertools import groupby
def group(flat):
	# Use a regular expression to split the string before the last part (repeat number)
	def split_key(s):
		return '-'.join(s.split('-')[0:7])

	# Sort the strings based on the non-repeat part
	sorted_strings = sorted(flat, key=split_key)
	
	# Group by the non-repeat part
	grouped_strings = [list(group) for _, group in groupby(sorted_strings, key=split_key)]
	
	return grouped_strings
def parse_command_line_arguments(program_name: str):
	epilog_string = ""

	parser = argparse.ArgumentParser(
		prog=program_name,
		description='Workflow simulator calibrator',
		epilog=epilog_string)

	try:
		parser.add_argument('-a ', '--simulator_args', type=str, metavar="<json args>", 
						help='Json string of arguments to give to siumulator')
		#parser.add_argument('-p', '--pickle', type=str, metavar="<pickle>", required=True,
		#					help='Pickled calibration to use')
		#parser.add_argument('-cn', '--computer_name', type=str, metavar="<computer name>", required=True,
		#					help='Name of this computer to add to the pickled file name')
		#parser.add_argument('-wn', '--workflow_name', type=str, metavar="<workflow name>", required=True,
		#					help='Name of the workflow to run the calibration/validation on')
		#parser.add_argument('-ar', '--architecture', type=str,
		#					metavar="[haswell|skylake|cascadelake|icelake]",
		#					choices=['haswell', 'skylake', 'cascadelake','icelake'], required=True,
		#					help='The computer architecture')
		#parser.add_argument('-al', '--algorithm', type=str,
		#					metavar="[grid|random|gradient|skopt.gp|skopt.gbrt|skopt.rf|skopt.et]",
		#					choices=['grid', 'random', 'gradient','skopt.gp','skopt.gbrt','skopt.rf','skopt.et'], required=True,
		#					help='The calibration algorithm')
		#parser.add_argument('-tl', '--time_limit', type=int, metavar="<number of second>", required=True,
		#					help='A training time limit, in seconds')
		parser.add_argument('-th', '--num_threads', type=int, metavar="<number of threads (default=1)>", nargs='?',
							default=1, help='A number of threads to use for training')
		#parser.add_argument('-n', '--estimate_run_time_only', action="store_true",
		#					help='A number of threads to use for training')
		parser.add_argument('-lf', '--loss_function', type=str,
							metavar="makespan, average_runtimes, max_runtimes",
							choices=['makespan', 'average_runtimes','max_runtimes'], nargs='?',
							default="makespan",
							help='The loss function to evaluate a calibration')
		parser.add_argument('-la', '--loss_aggregator', type=str,
							metavar="average_error, max_error",
							choices=['average_error', 'max_error'], nargs='?',
							default="average_error",
							help='The loss aggregator to evaluate a calibration')					
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
		parser.add_argument('-es', '--evaluation_set', type=str, nargs="*",default=None, 
							help='The list of json files to use for evaluation')
		return vars(parser.parse_args()), parser, None

	except argparse.ArgumentError as error:
		return None, parser, error



def main(args):
	
	#print(base64.urlsafe_b64encode(hashlib.md5(str(set(args['training_set'])).encode()).digest()))
	# Pickle results filename

	#training=group(args['training_set'])
	#print(training)
	sim_args=args['simulator_args']
	evaluation=group(args['evaluation_set'])
	pickle_file_name = f"{args['pickle']}-Evaluation-" \
					   f"{orderinvarient_hash(evaluation,8)}-" \
					   f"{orderinvarient_hash(sim_args,8)}
					   f"{args['loss_function']}-" \
					   f"{args['loss_aggregator']}.pickled"

	# If the pickled file already exists, then print a warning and move on
	if os.path.isfile(pickle_file_name):
		sys.stderr.write(f"There is already a pickled file '{pickle_file_name}'... Not doing anything!\n")
		sys.exit(1)

	#sys.stderr.write(f"repacking expiriments for {pickle_file_name}\n")

	#with open(args['pickle'], 'rb') as f:
	#	experiment_set = pickle.load(f)
	simulator = Simulator(args["compute_service_scheme"],
						  args["storage_service_scheme"],
						  args["network_topology_scheme"])

	experiment_set = ExperimentSet(simulator,
								   "random",
								   args["loss_function"],
								   args["loss_aggregator"],
								   0,
								   args["num_threads"])
	#experiment_set.algorithm = args["algorithm"]
	
	
	experiment_set.add_experiment(
		WorkflowSetSpec().set_workflows(evaluation),
		[
			WorkflowSetSpec().set_workflows(evaluation)
		])
		experiment_set.experiments[0].calibration=sim_args
	
	
		
	sys.stderr.write(f"\nCreated {len(experiment_set)} experiments...\n")
	#print(experiment_set.experiments[0].training_set_spec.workflows)
	#time_estimate_str = timedelta(seconds=experiment_set.estimate_run_time())
	#sys.stderr.write(f"Running experiments (should take about {time_estimate_str})\n")
	start = time.perf_counter()
	pickle_path=sys.argv[1]
	experiment_set.compute_all_evaluations()
	elapsed = int(time.perf_counter() - start)
	sys.stderr.write(f"Actually ran in {timedelta(seconds=elapsed)}\n")
	# except Exception as error:
	#	sys.stderr.write(str(type(error)))
	#	sys.stderr.write(f"Error while running experiments: {error}\n")
	#	sys.exit(1)
	# dont catch print exit errors.  Just let the error throw its self and python will give a much better print then still exit
	print(experiment_set.experiments[0].evaluation_losses)
	# Pickle it
	with open(pickle_file_name, 'wb') as f:
		pickle.dump(experiment_set, f)
	#sys.stderr.write(f"Pickled to ./{pickle_file_name}\n")
	print(pickle_file_name)
	return pickle_file_name
if __name__ == "__main__":
	args, parser, error = parse_command_line_arguments(sys.argv[0])
	# Parse command-line arguments
	if not args:
		sys.stderr.write(f"Error: {error}\n")
		parser.print_usage()
		sys.exit(1)
	main(args)
