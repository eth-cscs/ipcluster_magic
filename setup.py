import os
from setuptools import setup


version_py = os.path.join(os.path.dirname(__file__), 'ipcmagic', 'version.py')
version = {}
with open(version_py) as fp:
    exec(fp.read(), version)

with open("README.md", "r", encoding="utf-8") as fp:
    long_description = fp.read()

setup(
    name='ipcmagic-cscs',
    version=version['VERSION'],
    packages=['ipcmagic'],
    url='https://github.com/eth-cscs/ipcluster_magic',
    license='BSD 3-Clause',
    description='IPyParallel magics for Jupyter notebooks',
    long_description=long_description,
    long_description_content_type='text/markdown',
    install_requires=[
        'ipython>=6.3.0',
        'docopt>=0.6.2',
        'ipyparallel>=8.2.1',
    ],
    extras_require={
      "dask": ['dask[complete]>=2022.05.0']
    }
)
