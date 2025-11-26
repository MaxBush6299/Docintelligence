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


def summarize_text(text: str, prompt: str, max_completion_tokens: int | None = None) -> str:
	"""Summarize the given text using Azure OpenAI.
	
	Args:
		text: The text to summarize
		prompt: The system prompt for summarization
		max_completion_tokens: Optional token limit. If None, no limit is applied.
	"""

	if not isinstance(text, str) or not text:
		raise ValueError("text must be a non-empty string")

	deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT")
	if not deployment:
		raise RuntimeError("AZURE_OPENAI_DEPLOYMENT must be set")

	client = _get_client()

	# Build request parameters
	params = {
		"model": deployment,
		"messages": [
			{"role": "system", "content": prompt},
			{"role": "user", "content": text},
		],
	}
	
	# Only add max_completion_tokens if specified
	if max_completion_tokens is not None:
		params["max_completion_tokens"] = max_completion_tokens

	response: Any = client.chat.completions.create(**params)

	# Debug: log response details
	import logging
	logger = logging.getLogger(__name__)
	logger.info(f"OpenAI response: choices={len(response.choices)}, finish_reason={response.choices[0].finish_reason if response.choices else 'N/A'}")
	
	content = response.choices[0].message.content
	logger.info(f"OpenAI content: {repr(content)[:200]}")
	
	# Check for length-related issues
	if response.choices[0].finish_reason == "length":
		if max_completion_tokens is not None:
			logger.warning(f"OpenAI hit token limit (max_completion_tokens={max_completion_tokens})")
		else:
			logger.warning("OpenAI hit model's maximum token limit")
		if not content:
			logger.error("finish_reason='length' but content is empty - this is unexpected")
	
	return (content or "").strip()

