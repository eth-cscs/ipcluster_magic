import ipyparallel as ipp
import os
import pexpect
import socket
import time
from docopt import docopt, DocoptExit
from ipcmagic.utilities import Arguments
from ipcmagic.version import VERSION
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
      -m --mpi                 Run with MPI support (engines are
                               automatically distributed across nodes)
    """
    def __init__(self, shell):
        super().__init__(shell)
        self.__version__ = VERSION
        self.running = False

    def parse_args(self, line):
        # Valid syntax
        try:
            args = docopt(self.__doc__,
                          argv=line.split(),
                          version=self.__version__)
        # Invalid syntax
        # Return `None` when syntax is not valid
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

    def _wait_for_cluster(self, waiting_time=60):
        try:
            c = ipp.Client(timeout=waiting_time)
        except ipp.TimeoutError:
            self.stop_cluster()
            print('The connection request to the cluster controller '
                  'has timed out. Please, start the cluster again.')
            return

        # at this point the ipcontroller is running and we wait
        # for the engines to be ready
        try:
            c.wait_for_engines(int(self.args.num_engines),
                               timeout=waiting_time)
        except ipp.TimeoutError:
            self.stop_cluster()
            print('IPCMagic has failed to launch the engines. '
                  'Please, start the cluster again.')
            return

    def _launch_engines_local(self):
        self.controller = pexpect.spawn('ipcontroller --log-to-file')
        # some seconds need to pass between launching the ipcontroller
        # and launching the ipengines. Otherwise it might happen
        # that the controller doesn't notice that the engines have
        # started.
        time.sleep(3)
        self.engines = [pexpect.spawn('ipengine --log-to-file')
                        for i in range(int(self.args.num_engines))]
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
            f'srun -n {self.args.num_engines} ipengine '
            f'--location={hostname} --log-to-file')
        time.sleep(1)
        self.running = True
        self._wait_for_cluster(waiting_time=60)

    def launch_engines(self):
        if not self.running:
            if self.args.mpi:
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
        args_dict = self.parse_args(line)
        # if the argument list is not a valid one
        # self.parse_args returns `None`
        if not args_dict:
            return

        self.args = Arguments(args_dict)
        if self.args.start:
            self.launch_engines()
        elif self.args.stop:
            self.stop_cluster()
