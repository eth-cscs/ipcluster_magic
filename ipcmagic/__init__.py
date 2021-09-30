from ipcmagic.magics import IPClusterMagics
from IPython import get_ipython


__version__ = '1.0.1'

ip = get_ipython()
ipcluster_magics = IPClusterMagics(ip)
ip.register_magics(ipcluster_magics)
