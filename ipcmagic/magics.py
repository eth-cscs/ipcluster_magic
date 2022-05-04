import ipyparallel as ipp
import os
import socket
import time
import ipcmagic.dask_cluster as dask_cluster
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
      --dask                   Create a dask.distributed cluster
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
            'launcher': 'srun',
            'dask': False
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

        if parsed_args['launcher'] == 'local' and parsed_args['dask']:
            print("The 'local' launcher does not support dask")
            return

        return parsed_args

    def _wait_for_cluster_start(self, timeout=60):
        try:
            self.client = ipp.Client(timeout=timeout)
        except ipp.TimeoutError:
            self.stop_cluster()
            print('The connection request to the cluster controller '
                  'has timed out. Please, start the cluster again.')
            return

        # at this point the ipcontroller is running and we wait
        # for the engines to be ready
        try:
            self.client.wait_for_engines(int(self.args.num_engines),
                                         timeout=timeout)
        except ipp.TimeoutError:
            self.stop_cluster()
            print('IPCMagic has failed to launch the engines. '
                  'Please, start the cluster again.')
            return

    def _launch_engines_local(self):
        self.controller = run_command_async('ipcontroller --log-to-file')
        # Let some seconds pass between launching the ipcontroller
        # and launching the ipengines. Otherwise the controller
        # might not notice that the engines have started.
        time.sleep(3)
        self.engines = [run_command_async('ipengine --log-to-file')
                        for i in range(int(self.args.num_engines))]
        time.sleep(1)
        self.running = True
        self._wait_for_cluster_start(timeout=60)

    def _launch_engines_mpi(self):
        self.controller = run_command_async('ipcontroller --ip="*" '
                                            '--log-to-file')
        # Let some seconds pass between launching the ipcontroller
        # and launching the ipengines. Otherwise the controller
        # might not notice that the engines have started.
        time.sleep(3)
        hostname = socket.gethostname()
        launcher_np_opts = {
            'srun': '-n',
            'mpirun': '-np',
        }
        np_opt = launcher_np_opts[self.args.launcher]
        try:
            self.engines = run_command_async(
                f'{self.args.launcher} {np_opt} {self.args.num_engines} ipengine '  # noqa: E501
                f'--location={hostname} --log-to-file')
        except FileNotFoundError:
            print(f'Launcher not supported in this system: '
                  f'{self.args.launcher}')
            return

        time.sleep(1)
        self.running = True
        self._wait_for_cluster_start(timeout=60)

        if self.args.dask:
            try:
                self.dask_client = dask_cluster.activate(
                    self.client, self.args
                )
            except ModuleNotFoundError as err:
                print(f'The dask cluster failed to start: {err}')
                self.stop_cluster()
                return

    def launch_engines(self):
        if not self.running:
            if self.args.launcher == 'local':
                self._launch_engines_local()
            else:
                self._launch_engines_mpi()

        else:
            print("IPCluster is already running.")

    def _wait_for_cluster_shutdown(self, timeout=5):
        for i in range(timeout):
            # If `[self.controller] + self.engines` can be added
            # it means that the local launcher was used.
            try:
                procs = [self.controller] + self.engines
                returncodes = []
                returncodes = [p.poll() for p in procs]
            except TypeError:
                returncodes = [self.controller.poll(), self.engines.poll()]

            if None not in returncodes:
                return

            time.sleep(1)

        print('Some processes seem to have failed during shutdown. '
              'The kernel might have to be restarted.')

    def stop_cluster(self):
        # this function is called by `%ipcluster stop`, consequently the
        # `self.args` won't be the same arguments that were used to
        # start the cluster. The only argument will be `self.args.stop`
        if self.running:
            try:
                # if the the dask.distributed cluster was never started
                # then `self.dask_client` doesn't exist
                dask_cluster.deactivate(self.dask_client, self.client)
            except AttributeError:
                pass

            self.client.shutdown(targets='all', hub=True)
            self._wait_for_cluster_shutdown(timeout=5)
            self.client.close()
            self.running = False

            # disable the px and autopx magics
            ipy = get_ipython()
            del ipy.magics_manager.magics['cell']['px']
            for m in ['px', 'autopx', 'pxconfig']:
                del ipy.magics_manager.magics['line'][m]

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
