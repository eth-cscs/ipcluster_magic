# Adapted from https://github.com/mpi4py/mpi4py/blob/master/demo/osu_bw.py
# and https://mpi4py.readthedocs.io/en/stable/tutorial.html#cuda-aware-mpi-python-gpu-arrays
# http://mvapich.cse.ohio-state.edu/benchmarks/

from mpi4py import MPI
import cupy as cp
import os


def osu_bw(
    BENCHMARH = "MPI G2G Bandwidth Test",
    skip = 10,
    loop = 100,
    window_size = 64,
    skip_large = 2,
    loop_large = 20,
    window_size_large = 64,
    large_message_size = 8192,
    MAX_MSG_SIZE = 1<<22,
    ):

    comm = MPI.COMM_WORLD
    myid = comm.Get_rank()
    numprocs = comm.Get_size()

    cp.cuda.Device(myid).use()

    if numprocs != 2:
        if myid == 0:
            errmsg = "This test requires exactly two processes"
        else:
            errmsg = None
        raise SystemExit(errmsg)

    s_buf = cp.arange(MAX_MSG_SIZE, dtype='i')
    r_buf = cp.empty_like(s_buf)
    cp.cuda.get_current_stream().synchronize()

    if myid == 0:
        print ('# %s' % (BENCHMARH,))
    if myid == 0:
        print ('# %-8s%20s' % ("Size [B]", "Bandwidth [MB/s]"))

    message_sizes = [2**i for i in range(30)]
    for size in message_sizes:
        if size > MAX_MSG_SIZE:
            break
        if size > large_message_size:
            skip = skip_large
            loop = loop_large
            window_size = window_size_large

        iterations = list(range(loop+skip))
        window_sizes = list(range(window_size))
        requests = [MPI.REQUEST_NULL] * window_size
        #
        comm.Barrier()
        if myid == 0:
            s_msg = [s_buf, size, MPI.BYTE]
            r_msg = [r_buf,    4, MPI.BYTE]
            for i in iterations:
                if i == skip:
                    t_start = MPI.Wtime()
                for j in window_sizes:
                    requests[j] = comm.Isend(s_msg, 1, 100)
                MPI.Request.Waitall(requests)
                comm.Recv(r_msg, 1, 101)

            t_end = MPI.Wtime()
        elif myid == 1:
            s_msg = [s_buf,    4, MPI.BYTE]
            r_msg = [r_buf, size, MPI.BYTE]
            for i in iterations:
                for j in window_sizes:
                    requests[j] = comm.Irecv(r_msg, 0, 100)
                MPI.Request.Waitall(requests)
                comm.Send(s_msg, 0, 101)
        #
        if myid == 0:
            MB = size / 1e6 * loop * window_size
            s = t_end - t_start
            print ('%-10d%20.2f' % (size, MB/s))


    cp.allclose(s_buf, r_buf)


if __name__ == '__main__':
    osu_bw()
