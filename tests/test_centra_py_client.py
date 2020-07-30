#!/usr/bin/env python

"""Tests for `centra_py_client` package."""

import pytest
from unittest.mock import Mock, patch

from centra_py_client.centra_py_client import Client
from centra_py_client.centra_session import CentraSession


class TestClient:
    @patch("centra_py_client.centra_py_client.CentraSession.json_query")
    @patch("centra_py_client.centra_py_client.CentraSession.connect")
    def test_list_assets(self, mock_connect, mock_json_query):
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
        mock_connect.assert_called_once()
        mock_json_query.assert_called_once()
        assert fake_asset in returned_assets
