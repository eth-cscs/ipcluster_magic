import subprocess
import socket
import os
import pexpect
import signal
import time
import ipyparallel as ipp
from ipywidgets import IntProgress, HTML, VBox
from IPython.display import display
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
        prog_bar = IntProgress(min=0, max=waiting_time)
        prog_label = HTML()
        prog_box = VBox(children=[prog_label, prog_bar])
        display(prog_box)
        # display(prog_bar)

        prog_label.value = 'Setting up the IPCluster'

        try:
            c = ipp.Client()
        except ipp.TimeoutError:
            self.stop_cluster()
            prog_label.value = ('The connection request to the IPCluster has timed out. '
                                'Please, start the cluster again')
            return -1

        for t in range(waiting_time):
            time.sleep(1)
            prog_bar.value += 1
            if len(c.ids) == int(self._args['num_engines']):
                prog_bar.max = t
                prog_bar.bar_style = 'success'
                prog_bar.close()
                prog_label.value = 'IPCluster is ready! (%s seconds)' % t
                return 0

        prog_bar.bar_style = 'danger'
        self.stop_cluster()
        prog_bar.close()
        prog_label.value = ('IPCluster failed to start after %s seconds. '
                            'Please, start the cluster again' % t)
        return -1

        # while not len(c.ids) == int(self._args['num_engines']):
        #     time.sleep(1)
        #     time_counter += 1
        #     prog_bar.value += 1
        #     if time_counter > waiting_time:
        #         self.stop_cluster()
        #         return ('IPCluster failed to start after %s seconds. '
        #                 'Please, start the cluster again' % len(c.ids))

    def _launch_engines_local(self):
        if not self.running:
            self.controller = pexpect.spawn('ipcontroller --log-to-file')
            # some a seconds need pass a after launching the ipcontroller
            # before launching the ipengines. Otherwise it maigh happen
            # that the controller doesn't notice that the engines have
            # started.
            time.sleep(3)
            self.engines = [pexpect.spawn('ipengine --log-to-file')
                            for i in range(int(self._args['num_engines']))]
            # for i in self.engines:
            #     print('engine pid:', i.pid)

            time.sleep(1)
            # print('ctrler pid:', self.controller.pid)

            self.running = True

            self._wait_for_cluster(waiting_time=60)
        else:
            print("IPCluster is already running.")

    def _launch_engines_mpi(self):
        if not self.running:
            self.controller = pexpect.spawn('ipcontroller --ip="*" --log-to-file')
            # some a seconds need pass a after launching the ipcontroller
            # before launching the ipengines. Otherwise it maigh happen
            # that the controller doesn't notice that the engines have
            # started.
            time.sleep(3)
            hostname = socket.gethostname()
            self.engines = pexpect.spawn(
                'srun -n %s ipengine --location=%s --log-to-file' % (self._args['num_engines'], hostname))
            # print('engine pid', self.engines.pid)

            time.sleep(1)
            # print('ctrler pid:', self.controller.pid)

            self.running = True

            self._wait_for_cluster(waiting_time=60)
        else:
            print("IPCluster is already running.")

    def launch_engines(self):
        if self._args['mpi']:
            self._launch_engines_mpi()
        else:
            self._launch_engines_local()

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
