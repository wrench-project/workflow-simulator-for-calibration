# Workflow-execution simulator used for simulation calibration experiments

This simulator takes as input a single JSON file. The file `data/sample_input.json` for and example input.

## How to calibrate a simulator

The calibration is compatible with `Python <= 3.9`. Your first need to install DeepHyper:

```bash
python3.9 -m pip install -r calibration/requirements.txt
```

> Note that Python 3.10 breaks several things and is not yet supported.

To launch a simple exploration with `10` iterations, using [Ray](https://www.ray.io/) as distributed backend, you can run:

```bash
./calibration/calibrate.py --config calibration/config.json --iter 10
```

> By default, the script will detect the number of _physical_ cores and use that number to set up the number of workers.

Note that, when providing the flag `--all`, the script `calibrate.py` will perform two consecutives calibrations, one using **bayesian optimization (BO)** and one using a naive **random search (RS)** approach.

As result, you should get something similar to this:

```bash
================================================
=============== exp-b823c6aaee73 ===============
================================================
Best error:
        Bayesian Optimization    (BO): 12.693%
        Random Search - baseline (RS): 5.059%
================================================
```

`calibrate.py` creates a directory named `exp-{ID}` (`ID` is a random UUID) that contains several files:

+ **results.csv**: This file contains a summary of the _error_ reached for each method used. You also have a PDF plot with the same name;
+ **best-bo.json**:  The best configuration found by the Bayesian Optimization process as a JSON;
+ **bo.csv**:  This CSV file contains a line for each iteration ran by DeepHyper when using _Bayesian Optimization_ with the objective function value (i.e., simulator makespan) and the parameters values (payloads and properties);
+ **rs.csv**: This file is similar to **bo.csv** except that it contains data from the exploration when using _Random Search_. You have to use the flag `--all` to generate this file. This method is used as baseline comparison for other methods.
+ **best-rs.json**:  The best configuration found by the _Random Search_ process as a JSON;

> Note that you can re-run the simulator with the best configuration found by DeepHyper with `./workflow-simulator-for-calibration exp-{ID}/best-bo.json`.
