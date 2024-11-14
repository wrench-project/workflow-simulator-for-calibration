#!/usr/bin/env python3
import argparse
import sys
import pickle 

from Util import *



if __name__ == "__main__":
	if len(sys.argv<2):
		print(f"Usage:{sys.argv[0]} pickle_file") 
		exit()
	if len(sys.argv>2):
		print(f"{sys.argv[0]} * not supported, try find") 
		exit()
	pickle_path=sys.argv[1]
	with open(pickle_path, 'rb') as f:
		data = pickle.load(f)
	data.compute_all_evaluations()
	with open(pickle_path, 'wb') as f:
		pickle.dump(data, f)