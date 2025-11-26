import json
from http import HTTPStatus
from typing import Any, Dict

import azure.functions as func
import pytest
from function_app import http_start_impl


def _build_request(body: Dict[str, Any]) -> func.HttpRequest:
    return func.HttpRequest(
        method="POST",
        url="http://localhost:7071/api/process-document",
        headers={"Content-Type": "application/json"},
        params={},
        route_params={},
        body=json.dumps(body).encode("utf-8"),
    )


class DummyDurableClient:
    def __init__(self) -> None:
        self.started_with = None

    async def start_new(self, name: str, instance_id: str | None, payload: Dict[str, Any]):
        self.started_with = {"name": name, "instance_id": instance_id, "payload": payload}
        return "test-instance-id"

    def create_check_status_response(self, req: func.HttpRequest, instance_id: str) -> func.HttpResponse:
        return func.HttpResponse(
            json.dumps({"id": instance_id}),
            status_code=HTTPStatus.ACCEPTED,
            mimetype="application/json",
        )


@pytest.mark.asyncio
async def test_http_start_accepts_valid_payload_and_returns_status_urls():
    dummy_client = DummyDurableClient()
    req = _build_request({"documentId": "doc-123", "blobPath": "raw-pdfs/doc-123.pdf"})

    resp = await http_start_impl(req, client=dummy_client)  # type: ignore[arg-type]

    assert resp.status_code == HTTPStatus.ACCEPTED
    body = json.loads(resp.get_body())
    assert body["id"] == "test-instance-id"
    assert dummy_client.started_with["name"] == "main_orch"
    assert dummy_client.started_with["payload"] == {
        "documentId": "doc-123",
        "blobPath": "raw-pdfs/doc-123.pdf",
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload,expected_error",
    [
        ({}, "'documentId' (string) is required."),
        ({"documentId": "doc-123"}, "'blobPath' (string) is required."),
        ({"blobPath": "raw-pdfs/doc-123.pdf"}, "'documentId' (string) is required."),
    ],
)
async def test_http_start_rejects_invalid_payload(payload, expected_error):
    dummy_client = DummyDurableClient()
    req = _build_request(payload)

    resp = await http_start_impl(req, client=dummy_client)  # type: ignore[arg-type]

    assert resp.status_code == HTTPStatus.BAD_REQUEST
    body = json.loads(resp.get_body())
    assert body["error"] == expected_error
