import logging

import pyeodh.logger
from pyeodh.client import Client

pyeodh.logger.setup(logging.DEBUG)

__version__ = "0.0.1"
__all__ = ["Client"]
