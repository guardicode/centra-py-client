#!/usr/bin/env python
""" Tests for `centra_py_client` package. """
import uuid

from unittest import TestCase
from unittest.mock import patch, call
from callee import Contains
from centra_py_client.exceptions.centra_session import CentraAPIBaseError

from centra_py_client.centra_client import CentraClient
from centra_py_client.centra_session import CentraSession


class TestClient(TestCase):
    @staticmethod
    def get_mock_centra_client(**session_args):
        if 'login' not in session_args:
            session_args["login"] = False
        return CentraClient(CentraSession("fakeaddr", "fakeuser", "fakepassword", **session_args))

    @patch("centra_py_client.centra_client.CentraSession.query")
    def test_get_assets(self, mock_query):
        # arrange
        fake_asset = {"id": "deadbeef-1337-1337-1337deadbeef1337"}
        fake_asset_2 = {"id": "8eadbeef-1337-1337-1337deadbeef1338"}
        mock_query.return_value = {
            "objects": [fake_asset, fake_asset_2],
            "total_count": 2,
            "results_in_page": 2,
            "to": 2,
        }
        client = self.get_mock_centra_client()

        # act
        returned_assets = [asset for asset in client.get_assets()]

        # assert
        mock_query.assert_called_once()
        assert fake_asset in returned_assets

    @patch("centra_py_client.centra_client.CentraSession.query")
    def test_get_labels(self, mock_query):
        # arrange
        fake_label = {"id": "deadbeef-1337-1337-1337deadbeef1337"}
        fake_label_2 = {"id": "8eadbeef-1337-1337-1337deadbeef1338"}
        mock_query.return_value = {
            "objects": [fake_label, fake_label_2],
            "total_count": 2,
            "results_in_page": 2,
            "to": 2,
        }
        client = self.get_mock_centra_client()

        # act
        returned_labels = [label for label in client.get_labels()]

        # assert
        mock_query.assert_called_once()
        assert fake_label in returned_labels and fake_label_2 in returned_labels

    @patch("centra_py_client.centra_client.CentraSession.query")
    def test_add_label_to_assets(self, mock_query):
        # arrange
        fake_asset_id = str(uuid.uuid4())
        fake_asset_2_id = str(uuid.uuid4())
        fake_key = "key"
        fake_value = "value"
        fake_label_id = str(uuid.uuid4())

        mock_query.return_value = {
            "id": fake_label_id,
            "key": fake_key,
            "value": fake_value,
            "name": f"{fake_key}: {fake_value}"
        }
        client = self.get_mock_centra_client()

        # act
        response_label_id = client.add_label_to_assets([fake_asset_id, fake_asset_2_id], fake_key, fake_value)

        # assert
        mock_query.assert_called_once_with(
            Contains(f'assets/labels/{fake_key}/{fake_value}'),
            method="POST",
            data={"vms": [fake_asset_id, fake_asset_2_id]})
        self.assertTrue(response_label_id == fake_label_id)

    @patch("centra_py_client.centra_client.CentraSession.query")
    def test_delete_label_by_key_value(self, mock_query):
        label_id = "label_id"
        mock_query.return_value = {
            "objects": [{"id": label_id}],
            "total_count": 1,
            "results_in_page": 20,
            "to": 1,
        }

        client = self.get_mock_centra_client()
        key = "a_key"
        value = "a_value"
        client.delete_label_by_key_value(key, value)

        mock_query.assert_has_calls(calls=[call(Contains(label_id), method="DELETE")])

    @patch("centra_py_client.centra_client.CentraSession.login")
    @patch("centra_py_client.centra_client.CentraSession.query")
    def test_is_connected_sanity(self, mock_json_query, _):
        mock_json_query.return_value = {'total_count': 0, 'new_count': 0, 'items': []}
        client = CentraClient(CentraSession("fakeaddr", "fakeuser", "fakepassword"))
        assert client.is_connected
        mock_json_query.assert_called_once()

    @patch("centra_py_client.centra_client.CentraSession.login")
    @patch("centra_py_client.centra_client.CentraSession.query")
    def test_is_connected_not_connected(self, mock_json_query, _):
        def raise_an_error(param1):
            raise CentraAPIBaseError(f"{param1} testerror")
        mock_json_query.side_effect = raise_an_error
        client = CentraClient(CentraSession("fakeaddr", "fakeuser", "fakepassword"))
        assert not client.is_connected
        mock_json_query.assert_called_once()
