import json
from types import SimpleNamespace

import pytest

from utils import storage_utils


class DummyBlobClient:
    def __init__(self):
        self.uploaded = None
        self.exists_value = True
        self.download_content = b"{}"

    def upload_blob(self, data, overwrite=False):
        self.uploaded = (data, overwrite)

    def exists(self):
        return self.exists_value

    def download_blob(self):
        return SimpleNamespace(readall=lambda: self.download_content)


class DummyContainerClient:
    def __init__(self, blob_client):
        self._blob_client = blob_client
        self.requested_name = None

    def get_blob_client(self, name):
        self.requested_name = name
        return self._blob_client


class DummyBlobServiceClient:
    def __init__(self, container_client):
        self._container_client = container_client
        self.requested_container = None

    def get_container_client(self, name):
        self.requested_container = name
        return self._container_client


def test_write_and_read_json_blob_roundtrip(monkeypatch):
    blob_client = DummyBlobClient()
    container_client = DummyContainerClient(blob_client)
    service_client = DummyBlobServiceClient(container_client)

    monkeypatch.setattr(storage_utils, "_blob_service_client", service_client, raising=False)

    data = {"a": 1, "b": "two"}
    storage_utils.write_json_blob("cont", "blob.json", data)

    assert blob_client.uploaded is not None
    uploaded_bytes, overwrite = blob_client.uploaded
    assert overwrite is True
    assert json.loads(uploaded_bytes.decode("utf-8")) == data
    assert container_client.requested_name == "blob.json"
    assert service_client.requested_container == "cont"

    # Now simulate a download of that same payload
    blob_client.download_content = uploaded_bytes
    loaded = storage_utils.read_json_blob("cont", "blob.json")
    assert loaded == data


def test_blob_exists(monkeypatch):
    blob_client = DummyBlobClient()
    container_client = DummyContainerClient(blob_client)
    service_client = DummyBlobServiceClient(container_client)

    monkeypatch.setattr(storage_utils, "_blob_service_client", service_client, raising=False)

    blob_client.exists_value = True
    assert storage_utils.blob_exists("cont", "blob.json") is True

    blob_client.exists_value = False
    assert storage_utils.blob_exists("cont", "blob.json") is False
