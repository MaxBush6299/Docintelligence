import json
import os
from typing import Any

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient


_blob_service_client: BlobServiceClient | None = None


def _get_blob_service_client() -> BlobServiceClient:
	global _blob_service_client
	if _blob_service_client is None:
		account_url = os.environ.get("BLOB_ACCOUNT_URL")
		if not account_url:
			# Fall back to AzureWebJobsStorage connection string if needed
			conn_str = os.environ.get("AzureWebJobsStorage")
			if not conn_str:
				raise RuntimeError("BLOB_ACCOUNT_URL or AzureWebJobsStorage must be set")
			_blob_service_client = BlobServiceClient.from_connection_string(conn_str)
		else:
			# Use DefaultAzureCredential for identity-based auth (az login, managed identity, etc.)
			credential = DefaultAzureCredential()
			_blob_service_client = BlobServiceClient(account_url=account_url, credential=credential)
	return _blob_service_client


def get_blob_client(container: str, blob_name: str):
	service = _get_blob_service_client()
	container_client = service.get_container_client(container)
	return container_client.get_blob_client(blob_name)


def write_json_blob(container: str, blob_name: str, data: Any) -> None:
	blob_client = get_blob_client(container, blob_name)
	body = json.dumps(data, ensure_ascii=False).encode("utf-8")
	blob_client.upload_blob(body, overwrite=True)


def read_json_blob(container: str, blob_name: str) -> Any:
	blob_client = get_blob_client(container, blob_name)
	downloader = blob_client.download_blob()
	content = downloader.readall().decode("utf-8")
	return json.loads(content)


def blob_exists(container: str, blob_name: str) -> bool:
	blob_client = get_blob_client(container, blob_name)
	return blob_client.exists()

