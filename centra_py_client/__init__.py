"""Top-level package for centra-py-client."""

__author__ = """Yonatan Golan"""
__email__ = 'yonatan.golan@guardicore.com'
__version__ = '0.4.0'

from .centra_py_client import CentraClient as CentraClient  # noqa: F401
from .centra_session import CentraSession as CentraSession  # noqa: F401
from centra_py_client.exceptions.session import CentraAPIBaseError

import logging
logging.getLogger('guardicore').addHandler(logging.NullHandler())
