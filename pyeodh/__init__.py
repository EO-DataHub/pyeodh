import logging

import pyeodh.logging
from pyeodh.client import Client

pyeodh.logging.setup(logging.DEBUG)

__version__ = "0.0.1"
__all__ = ["Client"]
