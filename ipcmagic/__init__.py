import socket
import os
import pexpect
import time
import ipyparallel as ipp
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
  -m --mpi                 Run with mpi support
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
                  'timed out. Please, start the cluster again')
            return -1

        animation = "|/-\\"
        idx = 0
        waiting_msg = 'Setting up the IPCluster '
        for t in range(waiting_time):
            polling_rate = 0.4
            time.sleep(polling_rate)
            print(waiting_msg + animation[idx % len(animation)], end="\r")
            idx += 1
            if len(c.ids) == int(self._args['num_engines']):
                print('IPCluster is ready! (%d seconds)' % (t * polling_rate))
                return 0

        print('IPCluster failed to start after %d seconds. '
              'Please, start the cluster again' % (t * polling_rate))

        # make sure that no rogue ipc processes are left running
        # before exitring
        self.stop_cluster()
        return -1

    def _launch_engines_local(self):
        self.controller = pexpect.spawn('ipcontroller --log-to-file')
        # some a seconds to need pass a after launching the ipcontroller
        # before launching the ipengines. Otherwise it maigh happen
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
        # some a seconds need pass a after launching the ipcontroller
        # before launching the ipengines. Otherwise it maigh happen
        # that the controller doesn't notice that the engines have
        # started.
        time.sleep(3)
        hostname = socket.gethostname()
        self.engines = pexpect.spawn(
            'srun -n %s ipengine --location=%s '
            '--log-to-file' % (self._args['num_engines'], hostname))
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


ip = get_ipython()
ipcluster_magics = IPClusterMagics(ip)
ip.register_magics(ipcluster_magics)
