import ipyparallel as ipp
import os
import socket
import time
from docopt import docopt, DocoptExit
from ipcmagic.utilities import Arguments, run_command_async
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
      --launcher <str>         Job launcher (mpirun | srun | local)
    """

    def __init__(self, shell):
        super().__init__(shell)
        self.__version__ = VERSION
        self.running = False
        self.launcher_np_opts = {
            'srun': '-n',
            'mpirun': '-np',
        }

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
            'launcher': 'srun'
        }

        given_args = {key: val for key, val in args.items() if val}
        all_args = {**defaults, **given_args}

        # Remove '--' from args
        parsed_args = {key.replace('--', ''): val
                       for key, val in all_args.items()}

        valid_launchers = ['mpirun', 'srun', 'local']
        if parsed_args['launcher'] not in valid_launchers:
            print(f"Invalid option for `--launcher`: "
                  f"{parsed_args['launcher']} \n"
                  f"Valid options are: {valid_launchers}")
            return

        return parsed_args

    def _wait_for_cluster(self, waiting_time=60):
        try:
            self.client = ipp.Client(timeout=waiting_time)
        except ipp.TimeoutError:
            self.stop_cluster()
            print('The connection request to the cluster controller '
                  'has timed out. Please, start the cluster again.')
            return

        # at this point the ipcontroller is running and we wait
        # for the engines to be ready
        try:
            self.client.wait_for_engines(int(self.args.num_engines),
                                         timeout=waiting_time)
        except ipp.TimeoutError:
            self.stop_cluster()
            print('IPCMagic has failed to launch the engines. '
                  'Please, start the cluster again.')
            return

    def _launch_engines_local(self):
        self.controller = run_command_async('ipcontroller --log-to-file')
        # some seconds need to pass between launching the ipcontroller
        # and launching the ipengines. Otherwise it might happen
        # that the controller doesn't notice that the engines have
        # started.
        time.sleep(3)
        self.engines = [run_command_async('ipengine --log-to-file')
                        for i in range(int(self.args.num_engines))]
        time.sleep(1)
        self.running = True
        self._wait_for_cluster(waiting_time=60)

    def _launch_engines_mpi(self):
        self.controller = run_command_async('ipcontroller --ip="*" '
                                            '--log-to-file')
        # some seconds need to pass between launching the ipcontroller
        # and launching the ipengines. Otherwise it might happen
        # that the controller doesn't notice that the engines have
        # started.
        time.sleep(3)
        hostname = socket.gethostname()
        np_opt = self.launcher_np_opts[self.args.launcher]
        try:
            self.engines = run_command_async(
                f'{self.args.launcher} {np_opt} {self.args.num_engines} ipengine '  # noqa
                f'--location={hostname} --log-to-file')
        except FileNotFoundError:
            print(f'Non-supported launcher: {self.args.launcher}')
            return

        time.sleep(1)
        self.running = True
        self._wait_for_cluster(waiting_time=60)

    def launch_engines(self):
        if not self.running:
            if self.args.launcher != 'local':
                self._launch_engines_mpi()
            else:
                self._launch_engines_local()
        else:
            print("IPCluster is already running.")

    def _wait_for_cluster_shutdown(self, waiting_time=5):
        for i in range(waiting_time):
            # If `[self.controller] + self.engines` can be added
            # it means that the local launcher was used.
            try:
                procs = [self.controller] + self.engines
                returncodes = []
                # for p in procs:
                #     returncodes.append(p.poll())
                returncodes = [p.pol() for p in procs]

            except TypeError:
                returncodes = [self.controller.poll(), self.engines.poll()]

            if None not in returncodes:
                return

            time.sleep(1)

        print('Some processes seem to have failed during shutdown. '
              'The kernel might have to be restarted.')

    def stop_cluster(self):
        if self.running:
            self.client.shutdown(targets='all', hub=True)
            self._wait_for_cluster_shutdown(waiting_time=5)
            self.running = False

            # disable the px and autopx magics
            ip = get_ipython()
            del ip.magics_manager.magics['cell']['px']
            del ip.magics_manager.magics['line']['px']
            del ip.magics_manager.magics['line']['autopx']

            print('IPCluster stopped.')
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
