"""Main module."""

import logging

from centra_py_client.centra_session import CentraSession


class CentraClient:
    def __init__(self, centra_session: CentraSession):
        self.logger = logging.getLogger()
        self.centra_session = centra_session

    def list_assets(self, **filt):
        return self.centra_session.json_query(self.centra_session.urljoin_api('assets'), params=filt)['objects']

    def add_label_to_assets(self, asset_ids, label_key, label_value):
        """
        This was once add_visibility_label
        """
        endpoint = f'assets/labels/{label_key}/{label_value}'
        return self.centra_session.json_query(self.centra_session.urljoin_api(endpoint),
                                              method='POST', data={"vms": asset_ids})
