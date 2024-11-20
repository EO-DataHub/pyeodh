from pyeodh.client import Client
from pyeodh.logger import set_log_level
from pyeodh.logger import setup as setup_logs

setup_logs()

__version__ = "0.0.9"
__all__ = ["Client", "set_log_level"]
