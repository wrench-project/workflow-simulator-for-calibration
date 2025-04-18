import glob
import os
import sys
from glob import glob
from typing import List, Callable
import pickle
import base64
import hashlib 
import ast
import simcal as sc
import re
import json

from Simulator import Simulator
from WorkflowSimulatorCalibrator import WorkflowSimulatorCalibrator, CalibrationLossEvaluator, get_makespan
from Loss import *
_units={None:1,"":1,
"s":1,"ms":0.001,"us":0.000001,"ns":0.000000001,
"f":1,"Kf":1_000, "Mf":1_000_000,"Gf":1_000_000_000,
"Bps":1,"KBps":1_000,"MBps":1_000_000,"GBps":1_000_000_000,
"bps":1,"Kbps":1_000,"Mbps":1_000_000,"Gbps":1_000_000_000,
"b":1,"Kb":1_000,"Mb":1_000_000,"Gb":1_000_000_000,
"B":1,"KB":1_000,"MB":1_000_000,"GB":1_000_000_000}
def parseDoubleUnited(raw: str):
	#print(raw,re.match(r"(\d+\.?\d*)([a-zA-Z]+)*", raw).groups())
	result = re.match(r"(\d+\.?\d*)([a-zA-Z]+)*", raw).groups()
	return float(result[0])*_units[result[1]]
def load_json(path):
	with open(path) as json_file:
		return json.load(json_file)
def flatten(arr):
	flat_list = []
	for item in arr:
		if isinstance(item, list) or isinstance(item, tuple):
			flat_list.extend(flatten(item))  # Recursively flatten the nested list
		else:
			flat_list.append(item)  # Append non-list item
	return flat_list


def orderinvarient_hash(x,l=22):
	x=flatten(x)
	acc=bytearray(hashlib.md5(bytes(len(x))).digest())
	for i in x:
		tmp=hashlib.md5(i.encode()).digest()
		
		for j in range(len(acc)):
			#acc[j]^=tmp[j]
			acc[j]=(tmp[j]+acc[j])%256
	return base64.urlsafe_b64encode(acc)[:l].decode()
	






# def load_pickled_calibration(filepath: str,
#							 compute_service_scheme: str,
#							 storage_service_scheme: str,
#							 network_topology_scheme: str):
#	with open(filepath, 'rb') as file:
#		pickled_calibration = pickle.load(file)
#		calibration = pickled_calibration["calibration"]
#
#		# Consistency checking
#		if pickled_calibration["compute_service_scheme"] != compute_service_scheme:
#			sys.stderr.write(f"Loading calibration's compute service scheme ("
#							 f"{pickled_calibration['compute_service_scheme']}) "
#							 f"inconsistent with command-line arguments ({compute_service_scheme})")
#		if pickled_calibration["storage_service_scheme"] != storage_service_scheme:
#			sys.stderr.write(f"Loading calibration's storage service scheme ("
#							 f"{pickled_calibration['storage_service_scheme']}) "
#							 f"inconsistent with command-line arguments ({storage_service_scheme})")
#		if pickled_calibration["network_topology_scheme"] != network_topology_scheme:
#			sys.stderr.write(f"Loading calibration's' network topology scheme ("
#							 f"{pickled_calibration['network_topology_scheme']}) "
#							 f"inconsistent with command-line arguments ({network_topology_scheme})")
#
#		return pickled_calibration["calibration"], pickled_calibration["loss"]
#
#
# def save_pickled_calibration(filepath: str,
#							 calibration: dict[str, sc.parameters.Value],
#							 loss: float,
#							 compute_service_scheme: str,
#							 storage_service_scheme: str,
#							 network_topology_scheme: str,makespan: str):
#	to_pickle = {"calibration": calibration,
#				 "loss": loss,
#				 "compute_service_scheme": compute_service_scheme,
#				 "storage_service_scheme": storage_service_scheme,
#				 "network_topology_scheme": network_topology_scheme,"makespan":makespan}
#	# Save it
#	with open(filepath, 'wb') as f:
#		pickle.dump(to_pickle, f)


def relative_error(ground, target):
	return (target - ground) / ground
def compute_calibration(workflows: List[List[str]],
						algorithm: str,
						simulator: Simulator,
						loss_spec: str,
						loss_aggregator: str,
						time_limit: float, num_threads: int):
	calibrator = WorkflowSimulatorCalibrator(workflows,
											 algorithm,
											 simulator,
											 get_loss_function(loss_spec,loss_aggregator))

	calibration, loss = calibrator.compute_calibration(time_limit, num_threads)
	return calibration, loss


def evaluate_calibration(workflows: List[List[str]],
						 simulator: Simulator,
						 calibration: dict[str, sc.parameters.Value],
						 loss_spec: str,
						 loss_aggregator: str) -> float:
	evaluator = CalibrationLossEvaluator(simulator, workflows, get_loss_function(loss_spec,loss_aggregator))
	loss = evaluator(calibration)  # TODO Replace with None whenever simcal allows it
	return loss


class WorkflowSetSpec:
	def __init__(self):
		self.workflow_dir="."
		self.workflow_name="custom"
		self.architecture="custom"
		self.num_tasks_values=[]
		self.data_values=[]
		self.cpu_values=[]
		self.num_nodes_values=[]
		self.workflows: List[List[str]]=[[]]
		self.ivhash=orderinvarient_hash(self.workflows)
		
	def rehash(self):
		self.ivhash=orderinvarient_hash(self.workflows)
	
	def set_workflows(self,workflows: List[List[str]]):
		self.workflows=workflows
		self.rehash()
		return self
	def update_fields(self)	:
		workflow_name=""
		architecture=""
		data_values=set()
		cpu_values=set()
		num_nodes_values=set()
		num_tasks_values=set()
		for workflow_group in self.workflows:
			for workflow in workflow_group:
				tokens = workflow.split('/')[-1].split("-")
				#0-workflow
				#1-tasks
				#2-CPU 
				#3-Fixed (1.0 (sometimes))
				#4-data
				#5-architecture
				#6-Num nodes
				#7-trial number (inc)
				#8-timestamp
				if not workflow_name:
					workflow_name=tokens[0]
				elif workflow_name!=tokens[0]:
					workflow_name="various"
				if not architecture:
					architecture=tokens[5]
				elif architecture!=tokens[5]:
					architecture="various"	
				num_tasks_values.add(int(tokens[1]))
				cpu_values.add(int(tokens[2]))
				data_values.add(int(tokens[4]))
				num_nodes_values.add(int(tokens[6]))
		self.workflow_name=workflow_name
		self.architecture=architecture
		self.num_tasks_values=list(num_tasks_values)
		self.data_values=list(data_values)
		self.cpu_values=list(cpu_values)
		self.num_nodes_values=list(num_nodes_values)
	def populate(self, workflow_dir: str, workflow_name: str, architecture: str,
				 num_tasks_values: List[int], data_values: List[int], cpu_values: List[int],
				 num_nodes_values: List[int]):
		self.workflow_dir=workflow_dir
		self.workflow_name=workflow_name
		self.architecture=architecture
		self.num_tasks_values=num_tasks_values
		self.data_values=data_values
		self.cpu_values=cpu_values
		self.num_nodes_values=num_nodes_values
		self.workflows = []
		for num_tasks_value in num_tasks_values:
			for data_value in data_values:
				for cpu_value in cpu_values:
					for num_nodes_value in num_nodes_values:
						search_string = f"{self.workflow_dir}/{self.workflow_name}-"
						if num_tasks_value == -1:
							search_string += "*" + "-"
						else:
							search_string += str(num_tasks_value) + "-"
						if cpu_value == -1:
							search_string += "*" + "-"
						else:
							search_string += str(cpu_value) + "-"
						search_string += "*-"
						if data_value == -1:
							search_string += "*" + "-"
						else:
							search_string += str(data_value) + "-"
						search_string += f"{self.architecture}-"
						if num_nodes_value == -1:
							search_string += "*" + "-"
						else:
							search_string += str(num_nodes_value) + "-"
						search_string += "*.json"
						found_workflows = glob(search_string)
						if len(found_workflows) > 1:
							self.workflows.append([os.path.abspath(x) for x in found_workflows])
		self.rehash()
		sys.stderr.write(".")
		sys.stderr.flush()
		return self
		
	def get_workflow_set(self) -> List[List[str]]:
		return self.workflows

	def is_empty(self) -> bool:
		return len(self.workflows) == 0

	def __repr__(self):
		return f"#tasks: {self.num_tasks_values}, #nodes: {self.num_nodes_values}, " \
			   f"data: {self.data_values}, cpu: {self.cpu_values}"

	def __eq__(self, other: object):
		if not isinstance(other, WorkflowSetSpec):
			return NotImplemented
		return other.ivhash==self.ivhash


class Experiment:
	def __init__(self,
				 training_set_spec: WorkflowSetSpec,
				 evaluation_set_specs: List[WorkflowSetSpec]):

		self.training_set_spec = training_set_spec
		# Remove duplicates from the evaluation set specs
		no_dup_evaluation_set_specs = []
		for evaluation_set in evaluation_set_specs:
			if evaluation_set not in no_dup_evaluation_set_specs:
				no_dup_evaluation_set_specs.append(evaluation_set)
		self.evaluation_set_specs = no_dup_evaluation_set_specs

		self.calibration: dict[str, sc.parameters.Value] | None = None
		self.calibration_loss: float | None = None
		self.evaluation_losses: List[float] | None = None
		self.evaluation_makespans: List[float] | None = None

	def __eq__(self, other: object):
		if not isinstance(other, Experiment):
			return NotImplemented
		return (self.training_set_spec == other.training_set_spec) and \
			(self.evaluation_set_specs == other.evaluation_set_specs)

	def __repr__(self):
		eval_str = ""
		for i in range(0, len(self.evaluation_set_specs)):
			eval_str += f"  Evaluation: {self.evaluation_set_specs[i]}\n"
			eval_str += f"	loss={self.evaluation_losses[i]}\n"
		return f"Training: {self.training_set_spec}\n  loss={self.calibration_loss}\n  calibration=\"{self.calibration}\"\n{eval_str}"

	def __str__(self):
		return self.__repr__()
	

class ExperimentSet:
	def __init__(self, simulator: Simulator, algorithm: str, loss_function: str, loss_aggregator: str, time_limit: float, num_threads: int):
		self.simulator = simulator
		self.algorithm = algorithm
		self.loss_function = loss_function
		self.loss_aggregator = loss_aggregator
		self.time_limit = time_limit
		self.num_threads = num_threads
		self.experiments: List[Experiment] = []

	def add_experiment(self, training_set_spec: WorkflowSetSpec, evaluation_set_specs: List[WorkflowSetSpec]):
		if training_set_spec.is_empty():
			# Perhaps print a message?
			sys.stderr.write("Empty training set")	
			return False
		non_empty_evaluation_set_specs = []
		for evaluation_set_spec in evaluation_set_specs:
			if not evaluation_set_spec.is_empty():
				non_empty_evaluation_set_specs.append(evaluation_set_spec)
		#if len(non_empty_evaluation_set_specs) == 0:
			#sys.stderr.write("Empty evaluation set")	
			#return False

		xp = Experiment(training_set_spec, non_empty_evaluation_set_specs)
		if xp not in self.experiments:
			self.experiments.append(xp)

		return True

	def is_empty(self):
		return len(self.experiments) == 0

	def get_workflows(self):
		workflows = set({})
		for xp in self.experiments:
			workflows.add(xp.training_set_spec.workflow_name)
			for s in xp.evaluation_set_specs:
				workflows.add(s.workflow_name)
		return list(workflows)

	def get_workflow(self):
		if len(self.get_workflows()) > 1:
			raise Exception("Experiment set is for more than one workflow")
		else:
			return self.experiments[0].training_set_spec.workflow_name

	def get_architectures(self):
		architectures = set({})
		for xp in self.experiments:
			architectures.add(xp.training_set_spec.architecture)
			for s in xp.evaluation_set_specs:
				architectures.add(s.architecture)
		return list(architectures)

	def get_architecture(self):
		if len(self.get_architectures()) > 1:
			raise Exception("Experiment set is for more than one architecture")
		else:
			return self.experiments[0].training_set_spec.architecture

	def compute_all_calibrations(self):
		# Make a set of unique training_set_specs
		training_set_specs = []

		print("In compute all calibrations")

		for xp in self.experiments:
			if xp.training_set_spec not in training_set_specs:
				training_set_specs.append(xp.training_set_spec)

		# For each unique training_set_spec: compute the calibration and store it in the experiments
		count = 1
		for training_set_spec in training_set_specs:
			sys.stderr.write(f"  Computing calibration #{count}/{len(training_set_specs)}  "
							 f"({len(training_set_spec.get_workflow_set())} "
							 f"workflows, {self.algorithm}, "
							 f"{self.time_limit} sec, "
							 f"{self.num_threads} threads)...\n")

			count += 1
			calibration, calibration_loss = compute_calibration(
				training_set_spec.get_workflow_set(),
				self.algorithm,
				self.simulator,
				self.loss_function,
				self.loss_aggregator,
				self.time_limit,
				self.num_threads)

			if calibration is None:
				raise Exception("Calibration computed is None: perhaps a higher time limit?")
			# update all relevant experiments (inefficient, but shouldn't be too many xps)
			for xp in self.experiments:
				if xp.training_set_spec == training_set_spec:
					xp.calibration = calibration
					xp.calibration_loss = calibration_loss

	def compute_all_evaluations(self):
		# Here we're ok doing possible redundant work since evaluation is cheap
		count = 1
		for xp in self.experiments:
			sys.stderr.write(f"  Performing evaluation #{count}/{len(self.experiments)}...\n")
			count += 1
			xp.evaluation_losses = []
			xp.evaluation_makespans = []
			for evaluation_set_spec in xp.evaluation_set_specs:
				xp.evaluation_losses.append(evaluate_calibration(
					evaluation_set_spec.get_workflow_set(),
					self.simulator,
					xp.calibration,
					self.loss_function,
					self.loss_aggregator))
				makespans={}
				for workflow in evaluation_set_spec.get_workflow_set():
					for i,w in enumerate(workflow):
						with sc.Environment() as env:
							makespans[w]=ast.literal_eval(self.simulator.run(env, (w,xp.calibration)))
				xp.evaluation_makespans.append(makespans)
	def estimate_run_time(self):	
		training_set_specs = []
		for xp in self.experiments:
			if xp.training_set_spec not in training_set_specs:
				training_set_specs.append(xp.training_set_spec)
		num_calibrations = len(training_set_specs)
		num_evals = sum([len(x.evaluation_set_specs) for x in self.experiments])

		eval_time = 3  # Guess
		fudge = 1.0  # LOL

		return fudge * (num_calibrations * self.time_limit + num_evals * eval_time)

	def run(self):
		# Computing all needed calibrations (which can be redundant across experiments, so let's not be stupid)
		self.compute_all_calibrations()
		self.compute_all_evaluations()

	def __repr__(self):
		set_str = ""
		for xp in self.experiments:
			set_str += f"{xp}\n"
		return set_str

	def __len__(self):
		return len(self.experiments)

	def __getitem__(self, item):
		return self.experiments[item]  # delegate to li.__getitem__
