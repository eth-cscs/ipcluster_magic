import os
from setuptools import setup


version_py = os.path.join(os.path.dirname(__file__), 'ipcmagic', 'version.py')
version = {}
with open(version_py) as fp:
    exec(fp.read(), version)


setup(name='ipcluster_magics',
      version=version['VERSION'],
      packages=['ipcmagic'],
      url='https://github.com/eth-cscs/ipcluster_magic',
      license='BSD',
      description='IPyParallel Slurm magics for jupyterlab at CSCS',
      long_description=open('README.md').read(),
      install_requires=[
          'ipython>=6.3.0',
          'pexpect>=4.8.0',
          'docopt>=0.6.2',
          'ipyparallel>=7.0.1',
      ]
)
