#!/usr/bin/env python

"""Tests for `centra_py_client` package."""
import pytest
import uuid

from unittest import TestCase
from unittest.mock import Mock, patch, call
from callee import Contains
from centra_py_client.exceptions import ManagementAPIError

from centra_py_client.centra_py_client import CentraClient
from centra_py_client.centra_session import CentraSession


class TestClient(TestCase):
    @patch("centra_py_client.centra_py_client.CentraSession.connect")
    @patch("centra_py_client.centra_py_client.CentraSession.json_query")
    def test_list_assets(self, mock_json_query, _):
        # arrange
        fake_asset = {"_id": "deadbeef-1337-1337-1337deadbeef1337"}
        fake_asset_2 = {"_id": "8eadbeef-1337-1337-1337deadbeef1338"}
        mock_json_query.return_value = {
            "objects": [fake_asset, fake_asset_2]
        }
        client = CentraClient(CentraSession("fakeaddr", "fakeuser", "fakepassword"))

        # act
        returned_assets = client.list_assets()

        # assert
        mock_json_query.assert_called_once()
        assert fake_asset in returned_assets

    @patch("centra_py_client.centra_py_client.CentraSession.connect")
    @patch("centra_py_client.centra_py_client.CentraSession.json_query")
    def test_add_label_to_assets(self, mock_json_query, _):
        # arrange
        fake_asset_id = str(uuid.uuid4())
        fake_asset_2_id = str(uuid.uuid4())
        fake_key = "key"
        fake_value = "value"

        mock_json_query.return_value = {
            "id": str(uuid.uuid4()),
            "key": fake_key,
            "value": fake_value,
            "name": f"{fake_key}: {fake_value}"
        }
        client = CentraClient(CentraSession("fakeaddr", "fakeuser", "fakepassword"))

        # act
        response = client.add_label_to_assets([fake_asset_id, fake_asset_2_id], fake_key, fake_value)

        # assert
        mock_json_query.assert_called_once_with(
            Contains(f'assets/labels/{fake_key}/{fake_value}'),
            method="POST",
            data={"vms": [fake_asset_id, fake_asset_2_id]})

    @patch("centra_py_client.centra_py_client.CentraSession.connect")
    @patch("centra_py_client.centra_py_client.CentraSession.json_query")
    def test_get_labels_ids(self, mock_json_query, _):
        id1 = uuid.uuid4()
        id2 = uuid.uuid4()
        mock_json_query.return_value = {
            'objects': [
                {"id": id1},
                {"id": id2},
            ]
        }

        client = CentraClient(CentraSession("fakeaddr", "fakeuser", "fakepassword"))
        key = "a_key"
        value = "a_value"
        label_ids = client.get_labels_ids(key, value)

        assert set(label_ids) == {id1, id2}
        mock_json_query.assert_called_once_with(
            Contains("visibility/labels"),
            method="GET",
            params={"key": key, "value": value}
        )

    @patch("centra_py_client.centra_py_client.CentraSession.connect")
    @patch("centra_py_client.centra_py_client.CentraClient.get_labels_ids")
    @patch("centra_py_client.centra_py_client.CentraSession.json_query")
    def test_delete_label_by_key_value(self, mock_json_query, mock_get_label_ids, _):
        first_id = "first_id"
        second_id = "second_id"
        mock_get_label_ids.return_value = [first_id, second_id]
        # This makes the call to json_query return the last part of the uri which is the label ID.
        # That's what the actual delete_label API returns.
        mock_json_query.side_effect = lambda uri, method: uri.split("/")[-1]

        client = CentraClient(CentraSession("fakeaddr", "fakeuser", "fakepassword"))
        key = "a_key"
        value = "a_value"
        client.delete_label_by_key_value(key, value)

        mock_json_query.assert_has_calls(
            calls=[
                call(Contains(first_id), method="DELETE"),
                call(Contains(second_id), method="DELETE")
            ],
            any_order=True
        )

    @patch("centra_py_client.centra_py_client.CentraSession.connect")
    @patch("centra_py_client.centra_py_client.CentraSession.json_query")
    def test_is_connected_sanity(self, mock_json_query, _):
        mock_json_query.return_value = {'total_count': 0, 'new_count': 0, 'items': []}
        client = CentraClient(CentraSession("fakeaddr", "fakeuser", "fakepassword"))
        assert client.is_connected
        mock_json_query.assert_called_once()

    @patch("centra_py_client.centra_py_client.CentraSession.connect")
    @patch("centra_py_client.centra_py_client.CentraSession.json_query")
    def test_is_connected_not_connected(self, mock_json_query, _):
        def raise_an_error(param1):
            raise ManagementAPIError(f"{param1} testerror")
        mock_json_query.side_effect = raise_an_error
        client = CentraClient(CentraSession("fakeaddr", "fakeuser", "fakepassword"))
        assert not client.is_connected
        mock_json_query.assert_called_once()
