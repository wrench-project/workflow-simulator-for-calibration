./calibration/calibrate.py --config calibration/config.json --iter 10
## Workflow execution simulator used for simulation calibration experiments

Code tested with:
 - SimGrid master commit ID: `3863ea3407b8209a66dded84e28001f24225682c`
 - WRENCH master commit ID: `cb3befe95bf0f04052a8b37c37e0f8e1b0416428`
 - Wfcommons master commit ID: `29c69989fe5701bc07eb66c0077531f60e8a4414`
 - Boost: `1.80`
 - Python: `3.9`

---

## How to invoke the simulator stand-alone

This simulator takes as input a single JSON file. An example input file
is in `data/sample_input.json`. An invocation of the simulator could be:
```bash
./workflow-simulator-for-calibration data/sample_input.json
```
which will print three numbers of standard output formatted as `A:B:C`,
where `A` is the simulated makespan computed by the simulator (in seconds),
`B` is the actual makespan of the workflow, observed on a real platform
(see `data/sample_workflow.json`), and `C` is the relative error between
`A` and `B` computed as $C=\frac{\left| A - B \right|}{B}$.

## How to calibrate the simulator

### Installation

The calibration script is compatible with `Python <= 3.9` and requires to install DeepHyper:
to install DeepHyper as:

```bash
python3.9 -m pip install -r calibration/requirements.txt
```

> **Warning**: Python 3.10 breaks several things and is not yet supported.

There are other dependencies. The script `./chameleon_install_script.sh`
installs EVERYTHING, and would be useful for you to see how to install
missing dependencies on Ubuntu (including Python 3.9)


### Running the calibration script without Docker


To launch a simple exploration with `10` iterations you can run:

```bash
./calibration/calibrate.py --config calibration/config.json --iter 10
```

If you want to calibrate multiple for multiple workflows using $20$ cores on your machine, you can specify a list of workflows (which will override the workflow specified `data/sample_input.json`):

```bash
./calibration/calibrate.py --config calibration/config.json --workflows seismology.json genome-250-50-10-0.json --iter 200 --cores 20
```

> By default, the script will detect the number of _physical_ cores and set up one worker per core. 

Note that, when providing the flag `--all`, the script `calibrate.py` will perform two consecutive calibrations, one using **Bayesian optimization (BO)** and one using a naive **random search (RS)** approach.

The output should be similar to this:

```bash
=============== exp-55eb0d10da07 ===============
Best error:
	Bayesian Optimization    (BO): 1.375%
	Random Search - baseline (RS): 0.180%
```

`calibrate.py` creates a directory named `exp-{ID}` (`ID` is a random UUID) that contains several files:

+ **results.csv**: This file contains a summary of the _error_ reached for each method used. You also have a PDF plot with the same name;
+ **best-bo.json**:  The best configuration found by the Bayesian Optimization process as a JSON;
+ **bo.csv**:  This CSV file contains a line for each iteration ran by DeepHyper when using _Bayesian Optimization_ with the objective function value (i.e., simulator makespan) and the parameters values (payloads and properties);
+ **rs.csv**: This file is similar to **bo.csv** except that it contains data from the exploration when using _Random Search_. You have to use the flag `--all` to generate this file. This method is used as baseline comparison for other methods.
+ **best-rs.json**:  The best configuration found by the _Random Search_ process as a JSON;

> Note that you can re-run the simulator with the best configuration found by DeepHyper with `./workflow-simulator-for-calibration exp-{ID}/best-bo.json`.

## Running the calibration script with Docker

If you've installed everything on your host (e.g., by running the `chameleon_install_script.sh` script), then you can just run `callibrate.py` as described above, and likely you don't need Docker. 

If you have installed everything but the SimGrid/WRENCH/simulator, then you can tell the script to use the pre-built Docker image:

```bash
docker pull wrenchproject/workflow-calibration:latest
./calibration/calibrate.py --docker --config calibration/config.json --iter 10
```

If you have installed nothing, then you can run _everything_ in Docker:

```bash
docker pull wrenchproject/workflow-calibration:latest
docker run -it --rm -v `pwd`:/home/wrench wrenchproject/workflow-calibration:latest ./calibration/calibrate.py --config calibration/config.json --iter 10
```


#### How to read a configuration file

The field **calibration_ranges** defines, for each variable that can be calibrated (e.g., *scheduling_overhead*, *payloads*, etc), a range of possible values. For example *batch_scheduling_algorithm* can take three discrete values, *max_num_concurrent_data_connections* can range from 1 to 64. For some values like *payloads*, the values are ranging from $2^0$ to $2^20$ bytes.

#### Calibrate multiple workflows

Once the path in your config file `config.json` are correct, you can run `./run-calibration.sh -d $(pwd) -c config.json`. By default, the process will run 300 iterations per workflow without early stopping (i.e., process will not stop even if the objective does not improve) and will use all cores available (can be change with `--cores X`).

# TODO

Sofware:
 - [x] Kyle scripts
   - [x] Push scripts to repo in the calibration/ directory
   - [x] Make it so that the script includes the JSON calibration inline in the big result file, rather than reference some experiment hash
   - [x] Add an option --keep-exp-directory to the script, by default, the exp directory is removed
 - [x] calibrate.py
   - [x] Add "--timeout" argument to calibrate.py so that it's not longer harcoded to 5 minutes
   - [x] Check that the timeout actually works as intended (i.e., timeouts even if passed a huge number of iterations)
   - [x] If so, then just pass a huge number of iterations and just be time-out-based


Experimental ground truth data:
 - [X] All executions are using 16 cores on each compute node on CC
 - [ ] Henri is still running workflows

Calibration experiments:
 - [ ] Pick simulator "versions": `all_bare_metal`/`htcondor_bare_metal`, `submit_only`/`submit_and_compute_hosts`, and `one_link`/`many_links`/`one_link_then_many_links`
    - VERSIONSIMPLE: `all_bare_metal`/`submit_only`/`one_link` 
    - VERSIONCOMPLEX: `htcondor_bare_metal/submit_and_compute_hosts/one_link_then_many_links`
 - [ ] Buffer size: Experiment with it (calibrate it or not, as it impacts simulation time)
    - For now, it's being calibrated between 20MB and 30MB, which is weird
    - **For next runs, let's fix it to 100MB**
 - [ ] Non-overfitting experiments
    - Calibrate for one workflow application using n tasks, and see how good things are for more tasks
      - Subset of results: 
	- Arch: HASWELL
	- #nodes: 4 
	- workflows: chain, forkjoin, seismology, montage, genome
      - Question #1: How close is RS from BO for the VERSIONSIMPLE simulator and for VERSIONCOMPLEX?
        - Looks pretty close for VERSIONSIMPLE
	- Need to run it for VERSIONCOMPLEX
	- Plot on the x axis the calibration attempt sorted by increase %error for RS, and on the y axis the average %error (over all 5 trials) for RS and BO
        - If always close, then let's increase the ranges of, e.g., bandwidth
    - Calibrate for one workflow application using n nodes, and see how good things are for more nodes
    - Calibrate for one workflow using n nodes, and see how good things are for OTHER workflows using n nodes
    - There are other dimentions (number of tasks, data size)


