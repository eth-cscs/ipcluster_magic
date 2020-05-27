from distutils.core import setup


setup(name='ipcluster_magics',
    version='0.1',
    packages=['ipcmagic'],
    url='https://github.com/eth-cscs/ipcluster_magic',
    license='BSD',
    description='IPyParallel Slurm magics for jupyterlab at CSCS',
    long_description=open('README.md').read(),
    install_requires=[
        'ipython>=6.3.0',
        'pexpect>=4.8.0',
        'docoptr>==0.6.2'
    ]
)
