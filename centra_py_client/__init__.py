""" Top-level package for centra-py-client. """

__author__ = """Yonatan Golan"""
__email__ = 'yonatan.golan@guardicore.com'
__version__ = '0.4.0'

from .centra_client import CentraClient as CentraClient
from .centra_session import CentraSession as CentraSession
from .exceptions.centra_session import CentraAPIBaseError

import logging
logging.getLogger('guardicore').addHandler(logging.NullHandler())
