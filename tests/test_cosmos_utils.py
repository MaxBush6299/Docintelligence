from types import SimpleNamespace

from utils import cosmos_utils


class DummyContainer:
    def __init__(self):
        self.upserted = []

    def upsert_item(self, doc):
        self.upserted.append(doc)


class DummyDatabase:
    def __init__(self, container):
        self._container = container
        self.requested_container_args = None

    def create_container_if_not_exists(self, **kwargs):
        self.requested_container_args = kwargs
        return self._container


class DummyClient:
    def __init__(self, database):
        self._database = database
        self.requested_db = None

    def create_database_if_not_exists(self, name):
        self.requested_db = name
        return self._database


def test_get_documents_container_and_upsert(monkeypatch):
    container = DummyContainer()
    database = DummyDatabase(container)
    client = DummyClient(database)

    monkeypatch.setattr(cosmos_utils, "_cosmos_client", client, raising=False)

    cont = cosmos_utils.get_documents_container()
    assert cont is container
    assert database.requested_container_args["id"] == "documents"
    assert "/id" in database.requested_container_args["partition_key"]["paths"]

    doc = {"id": "doc1", "status": "ok"}
    cosmos_utils.upsert_document_record(doc)
    assert container.upserted == [doc]
