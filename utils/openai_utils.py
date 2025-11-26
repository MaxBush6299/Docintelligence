import os
from typing import Any

from openai import AzureOpenAI


_client: AzureOpenAI | None = None


def _get_client() -> AzureOpenAI:
	"""Get or create a cached AzureOpenAI client instance."""

	global _client
	if _client is None:
		endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
		api_key = os.environ.get("AZURE_OPENAI_API_KEY")
		if not endpoint:
			raise RuntimeError("AZURE_OPENAI_ENDPOINT must be set")

		_client = AzureOpenAI(
			api_key=api_key,
			api_version="2025-01-01-preview",
			azure_endpoint=endpoint,
		)

	return _client


def summarize_text(text: str, prompt: str, max_completion_tokens: int = 512) -> str:
	"""Summarize the given text using Azure OpenAI."""

	if not isinstance(text, str) or not text:
		raise ValueError("text must be a non-empty string")

	deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT")
	if not deployment:
		raise RuntimeError("AZURE_OPENAI_DEPLOYMENT must be set")

	client = _get_client()

	response: Any = client.chat.completions.create(
		model=deployment,
		messages=[
			{"role": "system", "content": prompt},
			{"role": "user", "content": text},
		],
		max_completion_tokens=max_completion_tokens,
	)

	# Debug: log response details
	import logging
	logger = logging.getLogger(__name__)
	logger.info(f"OpenAI response: choices={len(response.choices)}, finish_reason={response.choices[0].finish_reason if response.choices else 'N/A'}")
	
	content = response.choices[0].message.content
	logger.info(f"OpenAI content: {repr(content)[:200]}")
	
	return (content or "").strip()

