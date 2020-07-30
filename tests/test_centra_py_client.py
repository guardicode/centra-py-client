#!/usr/bin/env python

"""Tests for `centra_py_client` package."""
import pytest
import uuid

from unittest import TestCase
from unittest.mock import Mock, patch
from callee import Contains

from centra_py_client.centra_py_client import Client
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
        client = Client(CentraSession("fakeaddr", "fakeuser", "fakepassword"))

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
        client = Client(CentraSession("fakeaddr", "fakeuser", "fakepassword"))

        # act
        response = client.add_label_to_assets([fake_asset_id, fake_asset_2_id], fake_key, fake_value)

        # assert
        mock_json_query.assert_called_once_with(
            Contains(f'assets/labels/{fake_key}/{fake_value}'),
            method="POST",
            data={"vms": [fake_asset_id, fake_asset_2_id]})

