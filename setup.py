from distutils.core import setup


setup(name='ipcluster_magics',
    version='0.1',
    packages=['ipcmagic'],
    url='https://github.com/eth-cscs/ipcluster_magic',
    license='BSD',  # license='LICENSE.txt',
    description='IPyParallel Slurm magics for jupyterlab at CSCS',
    long_description=open('README.md').read(),
    install_requires=[
        'ipython>=6.1.0',
    ]
)
