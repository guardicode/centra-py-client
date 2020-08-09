"""Top-level package for centra-py-client."""

__author__ = """Yonatan Golan"""
__email__ = 'yonatan.golan@guardicore.com'
__version__ = '0.1.0'

import logging

from .centra_py_client import Client as Client
from .centra_py_client import CentraSession as CentraSession


logging.getLogger(__name__).addHandler(logging.NullHandler())

