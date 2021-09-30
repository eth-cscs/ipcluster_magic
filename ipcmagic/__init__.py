from ipcmagic.magics import IPClusterMagics
from ipcmagic.version import VERSION
from IPython import get_ipython


__version__ = VERSION

ip = get_ipython()
ipcluster_magics = IPClusterMagics(ip)
ip.register_magics(ipcluster_magics)
