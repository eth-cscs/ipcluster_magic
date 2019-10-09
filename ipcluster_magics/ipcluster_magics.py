# System
import subprocess
import os
import threading

# 3rd-party
from IPython import get_ipython 
from IPython.core.magic import line_magic, magics_class, Magics
from docopt import docopt, DocoptExit
import tempfile

@magics_class
class IPClusterMagics(Magics):
    """Launch an IPyParallel cluster.

Usage:
  %ipcluster start [options]
  %ipcluster start [options] -m <modules>...
  %ipcluster stop
  %ipcluster (-h | --help)
  %ipcluster --version
  
Options:
  -h --help                Show this screen.
  -v --version             Show version.
  -N --num_nodes <int>     Number of nodes (default 1).
  -n --num_engines <int>   Number of engines (default 1 per node).
  -m --modules <str>       Modules to load (default none).
  -e --env <str>           Virtual env to activate (default none).
  -t --time <time>         Time limit (default 30:00).
  -d --dir <path>          Directory to ipengines (default $HOME)
  -C --const <str>         SLURM contraint (default gpu).
  -A --account <str>       SLURM account (default none)
  -q --queue <str>         SLURM queue (default normal).
  -J --name <str>          Job name (default ipyparallel)
"""

    def __init__(self, shell):
        super().__init__(shell)
        self.define_strings()
        self.running = False
    
    def define_strings(self):
        self.__version__ = "%ipcluster 0.1"
        
        # If we want to use sbatch (we don't)
        self.header_template = """
#!/bin/bash -l
#SBATCH -J {name}
#SBATCH -q {queue}
#SBATCH -N {num_nodes}
#SBATCH -t {time}
#SBATCH -C {constraint}
#SBATCH -A {account}
"""
        
        # If we want to use salloc (we do)
        self.salloc_template = 'salloc -J {name} -q {queue} -N {num_nodes} -t {time} -C {const}  -A {account} bash {script}'

        self.module_template = """
# Load modules
mod="{module}"
module load "$mod"
echo "Loaded module $mod"
#export PATH=$PYTHONUSERBASE/bin:$PATH
"""
        self.env_template = """
# Enable venv
env="{env}"
source "$env"/bin/activate
echo "Activated venv $env"

"""
        self.engine_template = """
# This script runs from all compute nodes
hostname=$(hostname -i)
ipengine --log-to-file
echo "Started engine on $hostname."
"""

        self.controller_template = """       
# This script is run from head compute node (e.g. nid00001)

# Launch controller, listening on correct interface
#myip=$(ip addr show ipogif0 | grep '10\.' | awk '{{print $2}}' | awk -F'/' '{{print $1}}')
myip=$(hostname -i)
ipcontroller --ip="$myip" --log-to-file
echo "Started controller on '$myip'."
"""
        
        self.cluster_template = """
# This script runs from mom node (e.g. cmom05)
# Report job id
echo "$SLURM_JOBID" > {jobid_script}
# Get head compute node hostname
headnode=$(scontrol show job "$SLURM_JOBID" | grep BatchHost | awk -F= '{{print $2}}')
# Start controller
ssh -o LogLevel=error $headnode 'bash {controller_script}' > /dev/null &
sleep 10
echo "Started controller on $headnode"
# Start engines
srun -N {num_engines} -n {num_engines} -c 1 -s bash {engine_script}
"""

    def parse_args(self, line):
        # Valid syntax
        try:
            args = docopt(self.__doc__, argv=line.split(), version=self.__version__)
        # Invalid syntax
        except DocoptExit:
            print("Invalid syntax.")
            print(self.__doc__)
            return 
        # Other normal exit (--version)
        except SystemExit:
            args = {}
            
        defaults = {
            'start': None,
            'stop': None,
            '--name': 'ipyparallel',
            '--num_nodes': 1,
            '--modules': None,
            '--env': None,
            '--queue': 'normal',
            '--time': '30:00',
            '--account': None,
            '--const': 'gpu'
        }
        
        given = {key: val for key, val in args.items() if val}
        combined = {**defaults, **given}
        
        # Remove '--' from args
        parsed_args = {key.replace('--',''): val for key, val in combined.items()}
        
        # Set number of engines
        if 'num_engines' not in parsed_args.keys():
            parsed_args['num_engines'] = parsed_args['num_nodes']
        
        return parsed_args
    
    def load_modules(self, fh, modules):
        if modules:
            for module in modules:
                mod_str = self.module_template.format(module=module) 
                fh.write(mod_str)
    
    def activate_env(self, fh, env):
        if env:
            env_str = self.env_template.format(env=env)
            fh.write(env_str)
        
    def start_controller(self, fh):
        fh.write(self.controller_template)
        
    def start_engine(self, fh):
        fh.write(self.engine_template)
        
    def start_cluster(self, fh, num_engines, controller_script, engine_script, jobid_script):
        cluster_str = self.cluster_template.format(
            num_engines=num_engines,
            controller_script=controller_script,
            engine_script=engine_script,
            jobid_script=jobid_script
        )
        fh.write(cluster_str)
    
    def create_controller_script(self, fh, modules, env):
        self.load_modules(fh, modules)
        self.activate_env(fh, env)
        self.start_controller(fh)
        
        self.read_script(fh)
        
    def create_engine_script(self, fh, modules, env):
        self.load_modules(fh, modules)
        self.activate_env(fh, env)
        self.start_engine(fh)
        
        self.read_script(fh)
        
    def create_batch_script(self, fh, modules, env, num_engines, controller_script, engine_script, jobid_script):
        self.load_modules(fh, modules)
        self.activate_env(fh, env)
        self.start_cluster(fh, num_engines, controller_script, engine_script, jobid_script)
        
        self.read_script(fh)
        
    def read_script(self, fh):
        fh.seek(0)
        # print("Script:")
        # print(subprocess.check_output(['cat', fh.name]).decode())
        # print("EOF")
    
    def get_salloc_line(self, batch_script, args):
        return self.salloc_template.format(script=batch_script, **args)
    
    def system_thread(self, command, fhs=[]):
        def execute(cmd, fhs):
            # Run command
            get_ipython().system(cmd)
            
            # Close temporary files
            for fh in fhs:
                fh.close()
                
        thread = threading.Thread(target=execute, args=(command, fhs))
        thread.start()
    
    def submit_job(self, args):
        controller_prefix = os.path.join(os.environ['SCRATCH'], '.ipccontroller')
        engine_prefix = os.path.join(os.environ['SCRATCH'], '.ipcengine')
        batch_prefix = os.path.join(os.environ['SCRATCH'], '.ipcbatch')
        jobid_prefix = os.path.join(os.environ['SCRATCH'], '.ipcjobid')
        
        # Create temporary files
        # They'll be destroyed after submission
        engine_fh = tempfile.NamedTemporaryFile('w', prefix=engine_prefix)
        controller_fh = tempfile.NamedTemporaryFile('w', prefix=controller_prefix)
        batch_fh = tempfile.NamedTemporaryFile('w', prefix=batch_prefix)
        # Job ID will be written to this file
        jobid_fh = tempfile.NamedTemporaryFile('r', prefix=jobid_prefix)
        fhs = [controller_fh, engine_fh, batch_fh, jobid_fh]
        
        # Create controller script
        controller_script = controller_fh.name
        self.create_controller_script(
            controller_fh,
            args['modules'],
            args['env']
        )

        # Create engine script
        engine_script = engine_fh.name
        self.create_engine_script(
            engine_fh,
            args['modules'],
            args['env']
        )

        # Create batch script
        batch_script = batch_fh.name
        jobid_script = jobid_fh.name
        self.create_batch_script(
            batch_fh,
            args['modules'], 
            args['env'],
            args['num_engines'],
            controller_script,
            engine_script,
            jobid_script
        )

        # Run salloc
        salloc_line = self.get_salloc_line(batch_script, args)
        self.running = True
        # print(salloc_line)
        
        self.listen_for_jobid(jobid_fh)
        self.system_thread(salloc_line, fhs)

    def listen_for_jobid(self, jobid_fh):
        def listener():
            while True:
                jobid = jobid_fh.read().strip()
                if jobid:
                    self.jobid = jobid
                    return
            
            time.sleep(1)
            
        thread = threading.Thread(target=listener)
        thread.start()
        
    def stop_job(self):
        if self.running:
            scancel_line = 'scancel {}'.format(self.jobid)
            self.system_thread(scancel_line)
            self.running = False
            print("Stopped job {}.".format(self.jobid))
        else:
            print("IPCluster not running.")
    
    @line_magic
    def ipcluster(self, line):
        # Parse arguments
        args = self.parse_args(line)
        
        # Exit on invalid syntax
        if not args:
            return

        if args['start']:
            self.submit_job(args)
        elif args['stop']:
            self.stop_job()
    
ip = get_ipython()
ipcluster_magics = IPClusterMagics(ip)
ip.register_magics(ipcluster_magics)
