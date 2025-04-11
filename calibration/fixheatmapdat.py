from heatmapdata import *

def fix(data):
	singles=data["single_sample"]
	recs=data["single_workflow"]
	for time in singles.keys():
		for workflow in singles[time].keys():

				tasks=min(singles[time][workflow].keys())
				nodes=min(singles[time][workflow][tasks].keys())
				if tasks!=min(recs[time][workflow].keys() or recs!=min(singles[time][workflow][tasks].keys())):
					break
				recs[time][workflow][tasks][nodes]=singles[time][workflow][tasks][nodes]
	print(data)
print("data47=",end="")
fix(data47)
print("data=",end="")
fix(data)