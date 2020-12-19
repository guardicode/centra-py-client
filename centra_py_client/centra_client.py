import logging

from typing import List, Generator

from centra_py_client.centra_session import CentraSession
from centra_py_client.exceptions.centra_session import CentraAPIBaseError
from centra_py_client.exceptions.centra_client import CentraObjectNotFound

DEFAULT_NUM_OF_OBJECTS_PER_PAGE = 1000


class CentraClient:
    def __init__(self, centra_session: CentraSession):
        self.logger = logging.getLogger('guardicore.CentraClient')
        self.centra_session = centra_session

    @property
    def is_connected(self) -> bool:
        """
        Use this to test for connectivity.
        :return: True if Centra is connected and answering the API.
        """
        try:
            return self.get_system_notifications() is not None
        except CentraAPIBaseError as e:
            self.logger.debug(f"Error while checking connectivity: {e}")
            return False

    def logout(self) -> None:
        """ Logout from Centra API """
        self.centra_session.logout()

    def get_assets(self,
                   limit: int = None,
                   objects_per_page: int = DEFAULT_NUM_OF_OBJECTS_PER_PAGE,
                   **kwargs) -> Generator:
        """
        List the assets in Centra
        :param limit: Limit the amount of assets returned
        :param objects_per_page: Amount of asset objects to fetch from Centra API per page
        :param kwargs: The following additional parameters and filters are supported are:
                    sort: Sort the assets returned according to specif attribute (Default is -last_seen).
                    status: Get only assets matching the provided statuses. At least one of 'on', 'off', 'deleted'.
                    search: Get only assets whose name or ips contains he provided search string.
                    id: Filter assets whose
                    labels: Filter assets by matching labels, providing one or more label ids
                    label_groups: Filter assets by matching label groups, providing one or more label group ids
        :return: A generator yielding asset objects dictionaries one by one
        """
        for page in self.centra_session.paginate(endpoint='assets',
                                                 method='GET',
                                                 stop_after=limit,
                                                 objects_per_page=objects_per_page,
                                                 params=kwargs):
            for asset_obj in page:
                yield asset_obj

    def get_labels(self,
                   limit: int = None,
                   objects_per_page: int = DEFAULT_NUM_OF_OBJECTS_PER_PAGE,
                   **kwargs) -> Generator:
        """
        List the labels in Centra
        :param limit: Limit the amount of labels returned
        :param objects_per_page: Amount of labels objects to fetch from Centra API per page
        :param kwargs: The following additional parameters and filters are supported are:
                    sort: Sort the labels returned according to specif attribute. The default is key,value.
                    key: get only labels whose key is the provided key
                    value: get only labels whose value is the provided value
                    id: get the label whose id is the provided id
                    search: get only labels whose name (key and value combination) contains the provided search
                    string
                    dynamic_criteria_limit: Limit the amount of dynamic criteria returned for each label object. The
                    default is 500
        :return: A generator yielding label objects dictionaries one by one
        """
        if 'search' in kwargs:
            kwargs['text_search'] = kwargs['search']
            del(kwargs['search'])
        if 'id' in kwargs:
            kwargs['name'] = kwargs['id']
            del(kwargs['id'])

        for page in self.centra_session.paginate(endpoint='visibility/labels',
                                                 method='GET',
                                                 stop_after=limit,
                                                 objects_per_page=objects_per_page,
                                                 params=kwargs):
            for label_obj in page:
                yield label_obj

    def add_label_to_assets(self, asset_ids: List[str], label_key: str, label_value: str) -> str:
        """
        Add a label to assets by their asset ids.
        Note - If any of the  assets are already labeled with a label that has the provided label_key, they will be
        automatically removed from their current label and added to the new provided label.
        :param asset_ids: A list of asset ids to add the label to
        :param label_key: The label key, e.g. "Environment"
        :param label_value: The label key, e.g. "Production"
        :return: The id of the label with the provided label_key and label_value
        """
        endpoint = f'assets/labels/{label_key}/{label_value}'
        label_summary_object = self.centra_session.query(endpoint, method='POST', data={"vms": asset_ids})
        return label_summary_object['id']

    def delete_label_by_name(self, label_name: str) -> str:
        """
        Delete a label by its name.
        :param label_name: The label name as a string, e.g. "App: Accounting" or "Environment: Production"
        :raises CentraObjectNotFound: If no label was found in Centra matching the provided name
        :raises AssertionError: If more than one label was found in Centra matching the provided name. As label names
        should be unique, this indicates something might be wrong with the query itself or with Centra data.
        :returns The deleted label's id
        """
        key, value = label_name.split(":")
        return self.delete_label_by_key_value(key.strip(), value.strip())

    def delete_label_by_key_value(self, label_key: str, label_value: str) -> str:
        """
        Delete the label with the provided key and value.
        :param label_key: The label key, e.g. "Environment"
        :param label_value: The label value, e.g. "Production"
        :raises CentraObjectNotFound: If no label was found in Centra matching the provided key and value
        :raises AssertionError: If more than one label was found in Centra matching the provided key and value. As each
        combination of key and value should be unique, this indicates something might be wrong with the query itself
        or with Centra data.
        :return The deleted label's id
        """
        label_ids = [label['id'] for label in self.get_labels(key=label_key, value=label_value)]
        if len(label_ids) == 0:
            raise CentraObjectNotFound(f"The label '{label_key}: {label_value}' was not found in Centra")
        elif len(label_ids) > 1:
            raise AssertionError(f"More than one label was found in Centra matching the query key={label_key} and "
                                 f"value={label_value}")

        label_id = label_ids[0]
        self.logger.debug(f"Deleting the label {label_id} with the key {label_key} and the value {label_value}")
        endpoint = f'visibility/labels/{label_id}'
        return self.centra_session.query(endpoint, method='DELETE')

    def get_system_notifications(self):
        return self.centra_session.query('system-notifications')
