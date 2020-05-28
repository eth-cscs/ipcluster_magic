import reframe as rfm
import reframe.utility.sanity as sn
from reframe.core.backends import getlauncher


@rfm.simple_test
class IPCMagicCheck(rfm.RunOnlyRegressionTest):
    def __init__(self):
        self.descr = 'Distributed training with TensorFlow using ipyparallel'
        self.valid_systems = ['daint:gpu', 'dom:gpu']
        self.valid_prog_environs = ['PrgEnv-gnu']
        self.modules = ['ipcmagic/0.1-CrayGNU-19.10']
        self.pre_run = [
            # 'module load ipcmagic/0.1-CrayGNU-19.10',
            'module unload dask',
            'module load Horovod/0.16.4-CrayGNU-19.10-tf-1.14.0']
        self.num_tasks = 2
        self.num_tasks_per_node = 1
        self.executable = 'ipython'
        self.executable_opts = ['tf-hvd-sgd-ipc-tf-1.14.py']
        nids = sn.extractall(r'nid(?P<nid>\d+)',
                             self.stdout, 'nid', str)
        self.sanity_patterns = sn.all([
            sn.assert_ne(nids, []),
            sn.assert_ne(nids[0], nids[1])
        ])
        self.reference = {
            'daint:gpu': {
                'slope': (2.0, -0.1, 0.1, ''),
                'offset': (0.0, -0.1, 0.1, ''),
                'retries': (4, None, None, ''),
            },
            'dom:gpu': {
                'slope': (2.0, -0.1, 0.1, ''),
                'offset': (0.0, -0.1, 0.1, ''),
                'retries': (4, None, None, ''),
            }
        }
        self.perf_patterns = {
            'slope': sn.extractsingle(r'slope=(?P<slope>\S+)',
                                      self.stdout, 'slope', float),
            'offset': sn.extractsingle(r'offset=(?P<offset>\S+)',
                                       self.stdout, 'offset', float),
            'retries': self.retries()
        }
        self.maintainers = ['RS', 'TR']
        self.tags = {'production'}

    @rfm.run_before('run')
    def prepare_run(self):
        # Changing the job launcher since the `ipython`
        # need to be emitited without `srun`.
        self.job.launcher = getlauncher('local')()

    @sn.sanity_function
    def retries(self):
        return 4 - sn.count(sn.findall(r'IPCluster is already running.',
                                       self.stdout))
