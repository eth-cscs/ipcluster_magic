# IPyCluster Magics

Magic commands to support running MPI python code as well as multi-node Dask workloads on Jupyter notebooks.

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
