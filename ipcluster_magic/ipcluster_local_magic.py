import subprocess
import os
import pexpect
import signal
import time
from IPython import get_ipython
from IPython.core.magic import line_magic, magics_class, Magics
from docopt import docopt, DocoptExit


@magics_class
class IPClusterMagics(Magics):
    """engine an IPyParallel cluster.

Usage:
  %ipcluster start -n <num_engines> [options]
  %ipcluster stop
  %ipcluster (-h | --help)
  %ipcluster --version

Options:
  -h --help                Show this screen.
  -v --version             Show version.
  -n --num_engines <int>   Number of engines (default 1 per node).
"""
    def __init__(self, shell):
        super().__init__(shell)
        self.__version__ = '0.0.1'
        self.running = False

    def parse_args(self, line):
        # Valid syntax
        try:
            args = docopt(self.__doc__,
                          argv=line.split(),
                          version=self.__version__)
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
        }

        given = {key: val for key, val in args.items() if val}
        combined = {**defaults, **given}

        # Remove '--' from args
        parsed_args = {key.replace('--', ''): val
                       for key, val in combined.items()}

        return parsed_args

    def launch_engines(self, args):
        self.controller = pexpect.spawn('ipcontroller --log-to-file')
        # some a seconds need pass a after launching the ipcontroller
        # before launching the ipengines. Otherwise it maigh happen
        # that the controller doesn't notice that the engines have
        # started.
        time.sleep(3)
        # self.engines = [pexpect.spawn('ipengine --log-to-file')
        #                 for i in range(int(args['num_engines']))]
        self.engines = pexpect.spawn('srun -n %s ipengine --log-to-file' % args['num_engines'])
        print('engine pid', self.engines.pid)
        # for i in self.engines:
        #     print('engine pid:', i.pid)

        time.sleep(1)
        print('ctrler pid:', self.controller.pid)

        self.running = True

    def stop_engines(self):
        if self.running:
            self.controller.terminate()
            self.engines.terminate()
            #procs = [self.controller] + self.engines
            #for e in procs:
            #    e.terminate()
                # e.sendline('\003')
                # time.sleep(2)
                # e.kill(signal.SIGTERM)

            self.running = False
        else:
            print("IPCluster not running.")

    @line_magic
    def ipcluster(self, line):
        args = self.parse_args(line)

        if not args:
            return

        if args['start']:
            self.launch_engines(args)
        elif args['stop']:
            self.stop_engines()


ip = get_ipython()
ipcluster_magics = IPClusterMagics(ip)
ip.register_magics(ipcluster_magics)
