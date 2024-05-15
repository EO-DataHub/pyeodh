import logging

from pyeodh.client import Client
from pyeodh.logger import setup as setup_logs

setup_logs(logging.DEBUG)

__version__ = "0.0.1"
__all__ = ["Client"]
