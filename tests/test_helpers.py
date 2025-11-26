import os

import pytest

from utils import openai_utils


def test_summarize_text_uses_deployment_and_returns_string(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyChoices:
        def __init__(self, content: str) -> None:
            self.message = type("M", (), {"content": content})()

    class DummyResponse:
        def __init__(self, content: str) -> None:
            self.choices = [DummyChoices(content)]

    class DummyChat:
        def completions(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise AssertionError("completions attribute should not be used directly")

        def create(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            return DummyResponse("summary from dummy")

    class DummyClient:
        def __init__(self) -> None:
            self.chat = type("C", (), {"completions": DummyChat()})()

    # Ensure env var exists
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "dummy-deployment")

    # Patch the internal client getter to return our dummy client
    monkeypatch.setattr(openai_utils, "_client", DummyClient(), raising=False)

    result = openai_utils.summarize_text("some text", "a prompt", max_tokens=10)

    assert isinstance(result, str)
    assert "summary from dummy" in result
