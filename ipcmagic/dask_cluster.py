import getpass
import os
import tempfile
import time


def activate(ipp_client, args):
    nnodes = int(os.environ.get('SLURM_NNODES', 1))
    cpus_per_engine = os.cpu_count() * nnodes // int(args.num_engines)
    nthreads = int(os.environ.get('OMP_NUM_THREADS', cpus_per_engine))
    dask_client = ipp_client.become_dask(nthreads=nthreads)
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        dask_client.write_scheduler_file(tmp.name)

    print(f'dask-cluster {dask_client.status}\n')
    user = getpass.getuser()
    print(f'The dashboard can be seen at '
          f'https://{user}.jupyter.cscs.ch/user/{user}/proxy/8787/status ')
    connect_cmd = ('# connect to cluster',
                   'from dask.distributed import Client',
                   f"client = Client(scheduler_file='{dask_client.scheduler_file}')",  # noqa: E501
                   'client')
    get_ipython().set_next_input('\n'.join(connect_cmd))

    return dask_client


def deactivate(dask_client, ipp_client):
    if dask_client.status == 'running':
        dask_client.close()
        ipp_client.stop_dask()

    time.sleep(2)

    print(f'dask cluster {dask_client.status}')
