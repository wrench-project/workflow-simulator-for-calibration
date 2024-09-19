#!/usr/bin/env python3
import argparse
import matplotlib.pyplot as plt
from scipy.stats import variation
import numpy as np

from Util import *


def parse_command_line_arguments(program_name: str):
	epilog_string = ""

	parser = argparse.ArgumentParser(
		prog=program_name,
		description='Workflow simulator calibrator',
		epilog=epilog_string)

	try:

		parser.add_argument('-wd', '--workflow_dir', type=str, metavar="<workflow dir>", required=True,
							help='Directory that contains all workflow instances')

		return vars(parser.parse_args()), parser, None

	except argparse.ArgumentError as error:
		return None, parser, error


def main():
	from sklearn.metrics import r2_score
	print(r2_score([1, 3, 3, 3, 3, 6], [3, 3, 3, 3, 3, 3]))

	# Parse command-line arguments
	args, parser, error = parse_command_line_arguments(sys.argv[0])
	if not args:
		sys.stderr.write(f"Error: {error}\n")
		parser.print_usage()
		sys.exit(1)

	# Build lists of workflows
	search_string = f"{args['workflow_dir']}/" \
					f"*-" \
					f"*-" \
					f"*-" \
					f"*-" \
					f"*-" \
					f"*-" \
					f"*-*.json"
	workflows = glob(search_string)
	if len(workflows) == 0:
		sys.stdout.write(f"No workflows found ({search_string})\n")
		sys.exit(1)
	else:
		sys.stderr.write(f"Found {len(workflows)} to process...\n")

	# Build list of workflow names and architectures
	workflow_names = set({})
	architectures = set({})
	num_nodes = set({})

	for workflow in workflows:
		workflow = workflow.replace('\\', '/') # this is why we cant have nice things windows
		tokens = workflow.split('/')[-1].split("-")
		workflow_names.add(tokens[0])
		architectures.add(tokens[5])
		num_nodes.add(tokens[6])
		##0-workflow
		##1-tasks
		##2-CPU
		##3-Fixed (1.0 (sometimes))
		##4-data
		##5-architecture
		##6-Num nodes
		##7-trial number (inc)
		##8-timestamp
	print(workflow_names)
	workflow_names = sorted(list(workflow_names))
	architectures = sorted(list(architectures))
	num_nodes = sorted(list(num_nodes))
	

	for workflow_name in workflow_names:
		for architecture in architectures:
			for num_node in num_nodes:
				makespans_data = {}
				print(f"{workflow_name} on {architecture}:")
				search_string = f"{args['workflow_dir']}/" \
								f"{workflow_name}-" \
								f"*-" \
								f"*-" \
								f"*-" \
								f"*-" \
								f"{architecture}-" \
								f"{num_node}-*.json"
				workflows = glob(search_string)
				num_tasks_values = set({})
				cpu_values = set({})
				data_values = set({})
				num_nodes_values = set({})
				for workflow in workflows:
					tokens = workflow.split('/')[-1].split("-")
					num_tasks_values.add(int(tokens[1]))
					cpu_values.add(int(tokens[2]))
					data_values.add(int(tokens[4]))
					#num_nodes_values.add(int(tokens[6]))
				num_tasks_values = sorted(list(num_tasks_values))
				cpu_values = sorted(list(cpu_values))
				data_values = sorted(list(data_values))
				#num_nodes_values = sorted(list(num_nodes_values))
				
				
				for num_tasks in num_tasks_values:
					for cpu in cpu_values:
						for data in data_values:
							makespans = []
							#for num_nodes in num_nodes_values:
							search_string = f"{args['workflow_dir']}/{workflow_name}-{num_tasks}-{cpu}-1.0-{data}-{architecture}-{num_node}-*"
							workflows = glob(search_string)
							makespans.extend([get_makespan(workflow) for workflow in workflows])

							if not makespans:
								print(f"   no makespans found")
								continue
							
							key = f"{workflow_name} on {architecture} with {num_tasks} tasks {cpu} cpu and {data} data on {num_node} nodes"
							makespans_data[key] = makespans

				#colors = plt.cm.tab20(np.linspace(0, 1, len(makespans_data)))
				fig, ax = plt.subplots(figsize=(10, 6))
				for i, (key, makespans) in enumerate(makespans_data.items()):
					# Add some jitter to the x-coordinates
					x = np.full_like(makespans, i) + np.random.uniform(-0.1, 0.1, size=len(makespans))
					y = makespans
					ax.scatter(x, y, label=key,s=2)#,c='#000000')

				
				ax.set_xticks(range(len(makespans_data)))
				ax.set_xticklabels(makespans_data.keys(), rotation=90, ha='right',fontsize=4)
				ax.set_ylabel('Makespans')
				ax.set_title('Makespans per Workflow and Architecture')

				plt.tight_layout()
				plt.savefig(f"{workflow_name}_on_{architecture}_{num_node}.pdf")
				plt.close()


if __name__ == "__main__":
	main()
