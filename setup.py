from distutils.core import setup

setup(
    name='ipcluster_magics',
    version='0.1',
    license='BSD',
    description='IPyParallel Slurm Magics',
    packages={'ipcluster_magics'},
    install_requires=[
        'ipython>=6.1.0',
    ]
)
