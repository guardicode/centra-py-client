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

    def delete_label_by_name(self, label_name: str):
        key, value = label_name.split(": ")
        self.delete_label_by_key_value(key, value)

    def delete_label_by_key_value(self, label_key, label_value):
        """
        Delete a label.
        :param label_value: TODO
        :param label_key: TODO
        :return:
        """
        # first, get label ID
        label_ids = self.get_labels_ids(label_key, label_value)
        for label_id in label_ids:
            self.logger.debug(f"Trying to delete {label_id}")
            endpoint = f'visibility/labels/{label_id}'
            deleted_id = self.centra_session.json_query(
                self.centra_session.urljoin_api(endpoint),
                method='DELETE')
            assert deleted_id == label_id

    # TODO change signature to accept filt
    def get_labels_ids(self, label_key, label_value):
        """
        :param label_key: The label key, e.g. "Environment", "Role".
        :param label_value: The label's value, e.g. "Prod", "DB".
        :return: A list of label IDs (can be used for other API such as deleting labels by ID)
        """
        endpoint = f"visibility/labels"
        params = {
            "key": label_key,
            "value": label_value
        }
        # TODO move to generic get_labels with pagination
        list_of_matching_label_objects = self.centra_session.json_query(
            self.centra_session.urljoin_api(endpoint),
            method='GET',
            params=params
        )['objects']
        list_of_matching_labels = [x['id'] for x in list_of_matching_label_objects]
        return list_of_matching_labels
