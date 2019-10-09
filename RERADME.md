# IPython magic for launching IPyParallel clusters via Slurm 

```
Start an IPyParallel cluster.

Usage:
  %ipcluster start [options]
  %ipcluster start [options] -m <modules>...
  %ipcluster stop
  %ipcluster (-h | --help)
  %ipcluster --version

Options:
  -h --help                Show this screen.
  -v --version             Show version.
  -N --num_nodes <int>     Number of nodes (default 1).
  -n --num_engines <int>   Number of engines (default 1 per node).
  -m --modules <str>       Modules to load (default none).
  -e --env <str>           Conda env to load (default none).
  -t --time <time>         Time limit (default 30:00).
  -d --dir <path>          Directory to engine engines (default $HOME)
  -C --const <str>         SLURM contraint (default gpu).
  -q --queue <str>         SLURM queue (default normal).
  -a --account <str>       SLURM queue (default none).
  -J --name <str>          Job name (default ipyparallel)
```
