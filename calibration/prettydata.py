#!/usr/bin/env python3
from heatmapdata import *

def printData(name,data):
	print(name+"={")
	indent=1
	for sub in data:
		print("\t'"+sub+"':{")
		for time in data[sub]:
			print("\t\t"+str(time)+":{")
			for workflow in data[sub][time]:
				print("\t\t\t'"+workflow+"':{")
				print("\t\t\t\t"+str(data[sub][time][workflow]))
				print("\t\t\t},")
			print("\t\t},")
		print("\t},")		
	print("}")		
	
printData("data",data)
printData("data47",data47)