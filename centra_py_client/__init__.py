"""Top-level package for centra-py-client."""

__author__ = """Yonatan Golan"""
__email__ = 'yonatan.golan@guardicore.com'
__version__ = '0.2.0'

import logging

from .centra_py_client import CentraClient as CentraClient  # noqa: F401
from .centra_py_client import CentraSession as CentraSession  # noqa: F401


logging.getLogger(__name__).addHandler(logging.NullHandler())
