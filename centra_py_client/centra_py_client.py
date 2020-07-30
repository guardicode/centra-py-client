"""Main module."""

import logging

from centra_py_client.centra_session import CentraSession


class Client:
    def __init__(self, centra_session: CentraSession):
        self.logger = logging.getLogger()
        self.centra_session = centra_session

    def list_assets(self, **filt):
        return self.centra_session.json_query(self.centra_session.urljoin_api('assets'), params=filt)['objects']
