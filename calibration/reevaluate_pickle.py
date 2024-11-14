#!/usr/bin/env python3
import argparse
import sys
import pickle 

from Util import *



if __name__ == "__main__":
	if len(sys.args<2):
		print(f"Usage:{sys.args[0]} pickle_file") 
		exit()
	if len(sys.args>2):
		print(f"{sys.args[0]} * not supported, try find") 
		exit()
	pickle_path=sys.args[1]
	with open(pickle_path, 'rb') as f:
		data = pickle.load(f)
	data.compute_all_evaluations()
	with open(pickle_path, 'wb') as f:
		pickle.dump(data, f)