import logging
from typing import List

from centra_py_client.centra_session import CentraSession


class CentraClient:
    def __init__(self, centra_session: CentraSession):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.centra_session = centra_session

    def list_assets(self, **filt):
        return self.centra_session.json_query(self.centra_session.urljoin_api('assets'), params=filt)['objects']

    def add_label_to_assets(self, asset_ids: List[str], label_key: str, label_value: str) -> str:
        """
        Add a label to assets.
        Note - If the assets are already labeled with a label that has the provided label_key, they will be
        automatically removed from their current label and added to the new provided label.
        :param asset_ids: A list of asset ids to add the label to
        :param label_key: The label key, e.g. "Environment"
        :param label_value: The label key, e.g. "Production"
        :return: The id of the label with the provided label_key and label_value
        """
        endpoint = f'assets/labels/{label_key}/{label_value}'
        label_summary_object = self.centra_session.json_query(self.centra_session.urljoin_api(endpoint),
                                                              method='POST', data={"vms": asset_ids})
        return label_summary_object['id']

    def delete_label_by_name(self, label_name: str):
        """
        Delete a label by its name.
        :param label_name: The label name as a string, e.g. "App: Accounting" or "Environment: Production"
        """
        key, value = label_name.split(":")
        self.delete_label_by_key_value(key.strip(), value.strip())

    def delete_label_by_key_value(self, label_key, label_value):
        """
        Delete a label.
        :param label_key: The label key, e.g. "Environment"
        :param label_value: The label value, e.g. "Production"
        """
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
        list_of_matching_label_ids = [x['id'] for x in list_of_matching_label_objects]
        self.logger.debug(f"Found {len(list_of_matching_label_ids)} matching labels")
        return list_of_matching_label_ids

    def get_system_notifications(self):
        return self.centra_session.json_query(
            self.centra_session.urljoin_api('system-notifications')
        )

    @property
    def is_connected(self) -> bool:
        """
        Use this to test for connectivity.
        :return: True if Centra is connected and answering the API.
        """
        return self.get_system_notifications() is not None
