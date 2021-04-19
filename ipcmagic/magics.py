import ipcmagic
import ipyparallel as ipp
import os
import pexpect
import socket
import time
from docopt import docopt, DocoptExit
from IPython.core.magic import line_magic, magics_class, Magics


@magics_class
class IPClusterMagics(Magics):
    """Manage an IPyParallel cluster.

Usage:
  %ipcluster start -n <num_engines> [options]
  %ipcluster stop
  %ipcluster (-h | --help)
  %ipcluster --version

Options:
  -h --help                Show this screen.
  -v --version             Show version.
  -n --num_engines <int>   Number of engines 
  -m --mpi                 Run with mpi support (engines are distributed across nodes)
"""
    def __init__(self, shell):
        super().__init__(shell)
        self.__version__ = ipcmagic.__version__
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
            'mpi': False,
        }

        given = {key: val for key, val in args.items() if val}
        combined = {**defaults, **given}

        # Remove '--' from args
        parsed_args = {key.replace('--', ''): val
                       for key, val in combined.items()}

        return parsed_args

    def _wait_for_cluster(self, waiting_time):
        try:
            c = ipp.Client()
        except ipp.TimeoutError:
            self.stop_cluster()
            print('The connection request to the IPCluster has '
                  'timed out. Please, start the cluster again.')
            return -1

        animation = "|/-\\"
        idx = 0
        for t in range(waiting_time):
            polling_rate = 0.4
            time.sleep(polling_rate)
            total_sec = t * polling_rate
            print('Setting up the IPCluster '
                  f'{animation[idx % len(animation)]}', end='\r')
            idx += 1
            if len(c.ids) == int(self._args['num_engines']):
                print(f'IPCluster is ready! ({total_sec:.0f} seconds)')
                return 0

        print(f'IPCluster failed to start after {total_sec:.0f} seconds. '
              'Please, start the cluster again')

        # make sure that no rogue ipc processes are left running
        # before exitring
        self.stop_cluster()
        return -1

    def _launch_engines_local(self):
        self.controller = pexpect.spawn('ipcontroller --log-to-file')
        # some seconds need to pass between launching the ipcontroller
        # and launching the ipengines. Otherwise it might happen
        # that the controller doesn't notice that the engines have
        # started.
        time.sleep(3)
        self.engines = [pexpect.spawn('ipengine --log-to-file')
                        for i in range(int(self._args['num_engines']))]
        time.sleep(1)
        self.running = True
        self._wait_for_cluster(waiting_time=60)

    def _launch_engines_mpi(self):
        self.controller = pexpect.spawn('ipcontroller --ip="*" '
                                        '--log-to-file')
        # some seconds need to pass between launching the ipcontroller
        # and launching the ipengines. Otherwise it might happen
        # that the controller doesn't notice that the engines have
        # started.
        time.sleep(3)
        hostname = socket.gethostname()
        self.engines = pexpect.spawn(
            f'srun -n {self._args["num_engines"]} ipengine '
            f'--location={hostname} --log-to-file')
        time.sleep(1)
        self.running = True
        self._wait_for_cluster(waiting_time=60)

    def launch_engines(self):
        if not self.running:
            if self._args['mpi']:
                self._launch_engines_mpi()
            else:
                self._launch_engines_local()
        else:
            print("IPCluster is already running.")

    def stop_cluster(self):
        if self.running:
            # `self.args['mpi']` is not valid for `ipcluster stop`.
            # If `[self.controller] + self.engines` can not be added
            # it means that the `--mpi` option was used.
            try:
                procs = [self.controller] + self.engines
                for e in procs:
                    e.terminate()
                    time.sleep(.5)
            except TypeError:
                self.controller.terminate()
                time.sleep(.5)
                self.engines.terminate()

            self.running = False
        else:
            print("IPCluster not running.")

    @line_magic
    def ipcluster(self, line):
        self._args = self.parse_args(line)

        if not self._args:
            return

        if self._args['start']:
            self.launch_engines()
        elif self._args['stop']:
            self.stop_cluster()
