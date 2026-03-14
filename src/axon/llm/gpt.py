from __future__ import annotations

import json
import logging
import os
import time
from collections.abc import Callable
from typing import Any

from openai import APIError, APIStatusError, OpenAI, RateLimitError

from axon.llm.base import LLMProvider

logger = logging.getLogger(__name__)


def _resolve_api_key(api_key_env: str, default_env: str) -> str:
    api_key = os.environ.get(api_key_env, "")
    if api_key:
        return api_key
    if api_key_env != default_env:
        return api_key_env
    raise RuntimeError(
        f"No API key found. Set env var {default_env} or put the key in config.toml api_key_env"
    )


class GPTProvider(LLMProvider):
    def __init__(self, config: dict, client_factory: Callable[..., OpenAI] = OpenAI):
        llm_cfg = config["llm"]
        api_key_env = llm_cfg.get("api_key_env", "OPENAI_API_KEY")
        api_key = _resolve_api_key(api_key_env, "OPENAI_API_KEY")

        self._client = client_factory(api_key=api_key)
        self._model = llm_cfg.get("model", "gpt-5-mini")
        self._temperature = llm_cfg.get("temperature", 0.2)
        self._max_tokens = llm_cfg.get("max_tokens", 1024)
        self._max_retries = 4
        self._base_delay = 15.0

    def generate(self, prompt: str) -> str:
        response = self._call(
            input=prompt,
            text={"format": {"type": "text"}},
        )
        return self._extract_text(response)

    def generate_json(self, prompt: str, schema: dict | None = None) -> dict:
        input_text = prompt
        format_config: dict[str, Any]

        if schema is None:
            input_text = prompt + "\n\nIMPORTANT: Return ONLY a valid JSON object."
            format_config = {"type": "json_object"}
        else:
            format_config = {
                "type": "json_schema",
                "name": schema["name"],
                "schema": schema["schema"],
                "strict": True,
            }

        response = self._call(
            input=input_text,
            text={"format": format_config},
        )
        return json.loads(self._extract_text(response))

    def _call(self, **kwargs: Any) -> Any:
        for attempt in range(self._max_retries):
            try:
                return self._client.responses.create(
                    model=self._model,
                    temperature=self._temperature,
                    max_output_tokens=self._max_tokens,
                    **kwargs,
                )
            except Exception as exc:
                if attempt >= self._max_retries - 1 or not self._should_retry(exc):
                    raise

                delay = self._retry_delay(exc, attempt)
                logger.warning(
                    "%s (attempt %d/%d). Waiting %.0fs...",
                    "Rate limited" if isinstance(exc, RateLimitError) else f"API error: {exc}",
                    attempt + 1,
                    self._max_retries,
                    delay,
                )
                time.sleep(delay)

        raise RuntimeError("OpenAI request failed without raising an exception")

    @staticmethod
    def _extract_text(response: Any) -> str:
        text = getattr(response, "output_text", "")
        if text:
            return text

        for item in getattr(response, "output", []):
            for content in getattr(item, "content", []):
                if getattr(content, "type", "") in {"output_text", "text"}:
                    content_text = getattr(content, "text", "")
                    if content_text:
                        return content_text

        raise ValueError("OpenAI response did not contain text output")

    @staticmethod
    def _should_retry(exc: Exception) -> bool:
        if isinstance(exc, APIStatusError):
            return exc.status_code == 429 or exc.status_code >= 500
        if isinstance(exc, (RateLimitError, APIError)):
            return True
        return False

    def _retry_delay(self, exc: Exception, attempt: int) -> float:
        if isinstance(exc, RateLimitError):
            return self._base_delay * (2**attempt)
        return 5.0 * (2**attempt)
