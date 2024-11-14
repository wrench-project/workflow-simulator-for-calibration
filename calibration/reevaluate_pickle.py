#!/usr/bin/env python3
import argparse
import sys
import pickle 

from Util import *



if __name__ == "__main__":
	with open(pickle_path, 'rb') as f:
		data = pickle.load(f)
	data.compute_all_evaluations()
	with open(pickle_path, 'wb') as f:
		pickle.dump(data, f)