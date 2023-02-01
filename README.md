# Workflow-execution simulator used for simulation calibration experiments

This simulator takes as input a single JSON file. The file `data/sample_input.json` is a good example. For example:
```bash
./workflow-simulator-for-calibration data/sample_input.json
```
which should return 3 numbers formatted as `A:B:C`, where `A` is the simulated makespan computed by the simulator (in secondes),
`B` is the real makepsan of the workflow, observed on a real platform (see `data/sample_workflow.json`), finally `C` is the relative error between `A` and `B` computed as $C=\frac{\left| A - B \right|}{B}$.

## How to calibrate a simulator

The calibration script is compatible with `Python <= 3.9`. Your first need to install DeepHyper:

```bash
python3.9 -m pip install -r calibration/requirements.txt
```

> **Warning**: Python 3.10 breaks several things and is not yet supported.

To launch a simple exploration with `10` iterations, using [Ray](https://www.ray.io/) as distributed back-end, you can run:

```bash
./calibration/calibrate.py --config calibration/config.json --iter 10
```

> By default, the script will detect the number of _physical_ cores and use that number to set up the number of workers.

Note that, when providing the flag `--all`, the script `calibrate.py` will perform two consecutive calibrations, one using **Bayesian optimization (BO)** and one using a naive **random search (RS)** approach.

As result, you should get an output similar to this:

```bash
=============== exp-seismology-250-50-10-0-55eb0d10da07 ===============
Best error:
	Bayesian Optimization    (BO): 1.375%
	Random Search - baseline (RS): 0.180%
```

`calibrate.py` creates a directory named `exp-{workflow}-{ID}` (`ID` is a random UUID) that contains several files:

+ **results.csv**: This file contains a summary of the _error_ reached for each method used. You also have a PDF plot with the same name;
+ **best-bo.json**:  The best configuration found by the Bayesian Optimization process as a JSON;
+ **bo.csv**:  This CSV file contains a line for each iteration ran by DeepHyper when using _Bayesian Optimization_ with the objective function value (i.e., simulator makespan) and the parameters values (payloads and properties);
+ **rs.csv**: This file is similar to **bo.csv** except that it contains data from the exploration when using _Random Search_. You have to use the flag `--all` to generate this file. This method is used as baseline comparison for other methods.
+ **best-rs.json**:  The best configuration found by the _Random Search_ process as a JSON;

> Note that you can re-run the simulator with the best configuration found by DeepHyper with `./workflow-simulator-for-calibration exp-{ID}/best-bo.json`.

## How to calibrate Pegasus Workflows

You have three scripts under `utils/`:
- `pegasus-submit-to-json.py`: takes on Pegasus submit directory (like `run0000/` etc) and produces workflow compatible with `calibrate.py` (JSON file)
- `convert-submit-dirs.sh`: converts a directory `dir` containing Pegasus submit directories with `./convert-submit-dirs.sh -d dir`
- `run-calibration.sh`: takes a directory `dir` containing workflows represented as JSON files and calibrate each of them
