import simcal as sc
from statistics import mean

from typing import List, Callable

def get_loss_function(loss_spec: str,aggregation: str) -> Callable:
	return LossHandler(loss_spec,aggregation)

def void(x: dict):
	return 0

def average_runtimes(x: dict):
	loss = 0
	count = 0
	for task in x['tasks']:
		real = float(x['tasks'][task]["real_duration"])
		sim = float(x['tasks'][task]["simulated_duration"])
		loss += abs(real-sim)/real
		count += 1
	if count == 0:
		return float('inf')
	return loss/count
	
def max_runtimes(x: dict):
	loss = 0
	if len(task['tasks']) == 0:
		return float('inf')
	for x in task['tasks']:		
		real = float(x['tasks'][task]["real_duration"])
		sim = float(x['tasks'][task]["simulated_duration"])
		loss = max(loss,abs(real-sim)/real)
	return loss	
	
class LossHandler:
	def __init__(self,loss_spec: str,aggregation: str):
		if aggregation == "average_error":
			self.method = mean
		elif aggregation == "max_error":
			self.method = max
		else:
			raise Exception(f"Unknown loss aggrigation name '{aggregation}'")
			
		if loss_spec == "makespan":
			self.loss_spec = void
		elif loss_spec == "average_runtimes":
			self.loss_spec = average_runtimes
		elif loss_spec == "max_runtimes":
			self.loss_spec = max_runtimes
		else:
			raise Exception(f"Unknown loss loss_spec name '{loss_spec}'")
	
	def __call__(self,output: List[dict]):
		losses = []
		print(output)
		for x in output:
			real_makespan = float(x["real_makespan"])
			simulated_makespan = float(x["simulated_makespan"])
			makespan_loss = abs(real_makespan-simulated_makespan)/real_makespan
			sub_loss = self.loss_spec(x)
			losses.append(makespan_loss+sub_loss)
			
		return self.method(losses)	