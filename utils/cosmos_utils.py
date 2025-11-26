import os
from typing import Any, Dict

from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential


_cosmos_client: CosmosClient | None = None


def _get_cosmos_client() -> CosmosClient:
	global _cosmos_client
	if _cosmos_client is None:
		endpoint = os.environ.get("COSMOS_ENDPOINT")
		if not endpoint:
			raise RuntimeError("COSMOS_ENDPOINT must be set")
		# Use DefaultAzureCredential for identity-based auth (az login, managed identity, etc.)
		credential = DefaultAzureCredential()
		_cosmos_client = CosmosClient(endpoint, credential=credential)
	return _cosmos_client


def get_documents_container():
	client = _get_cosmos_client()
	db_name = os.environ.get("COSMOS_DB", "docum")
	# Use get_database_client instead of create_database_if_not_exists
	# The database and container must be pre-created in Azure
	database = client.get_database_client(db_name)
	container = database.get_container_client("documents")
	return container


def upsert_document_record(document: Dict[str, Any]) -> None:
	container = get_documents_container()
	container.upsert_item(document)

