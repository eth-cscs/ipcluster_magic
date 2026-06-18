# IPyCluster Magics

Jupyter notebook magic commands for running MPI-based Python code and multi-node Dask workloads directly from notebooks.
It supports `mpirun` and `srun` (Slurm) launchers, as well as a non-MPI launcher for workloads that do not require inter-rank communication.

## Installation

This package is called `ipcmagic-cscs` in [PyPI](https://pypi.org/project/ipcmagic-cscs). It can be installed with
```bash
pip install ipcmagic-cscs[dask]
```
This installs all `ipcmagic-cscs` dependencies including Dask (`dask[complete]`).

If the Dask support is not needed, `ipcmagic-cscs` can be installed with
```bash
pip install ipcmagic-cscs
```
which doesn't include the installation of Dask and it's dependencies.

## Usage

See examples [here](https://github.com/eth-cscs/ipcluster_magic/tree/master/examples).
