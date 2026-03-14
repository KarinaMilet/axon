from __future__ import annotations

import json
import logging
import os
import re
import time

from google import genai
from google.genai import types

from axon.llm.base import LLMProvider

logger = logging.getLogger(__name__)


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```\w*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    return text.strip()


class GeminiProvider(LLMProvider):
    def __init__(self, config: dict):
        llm_cfg = config["llm"]
        api_key_env = llm_cfg.get("api_key_env", "GEMINI_API_KEY")
        api_key = os.environ.get(api_key_env, "") or api_key_env
        if not api_key:
            raise RuntimeError(
                "No API key found. Set env var GEMINI_API_KEY or put the key in config.toml api_key_env"
            )

        self._client = genai.Client(api_key=api_key)
        self._model = llm_cfg.get("model", "gemini-2.0-flash")

        self._gen_config = types.GenerateContentConfig(
            max_output_tokens=llm_cfg.get("max_tokens", 1024),
            temperature=llm_cfg.get("temperature", 0.2),
        )
        self._json_config = types.GenerateContentConfig(
            max_output_tokens=llm_cfg.get("max_tokens", 1024),
            temperature=llm_cfg.get("temperature", 0.2),
            response_mime_type="application/json",
        )
        self._max_retries = 4
        self._base_delay = 15.0

    def generate(self, prompt: str) -> str:
        return self._call(prompt, self._gen_config)

    def generate_json(self, prompt: str, schema: dict | None = None) -> dict:
        text = self._call(prompt, self._json_config)
        text = _strip_code_fences(text)
        return json.loads(text)

    def _call(self, prompt: str, config: types.GenerateContentConfig) -> str:
        for attempt in range(self._max_retries):
            try:
                response = self._client.models.generate_content(
                    model=self._model,
                    contents=prompt,
                    config=config,
                )
                return response.text
            except Exception as e:
                err_str = str(e).lower()
                if attempt < self._max_retries - 1:
                    is_rate_limit = "429" in str(e) or "quota" in err_str or "resource_exhausted" in err_str
                    delay = self._base_delay * (2 ** attempt) if is_rate_limit else 5.0 * (2 ** attempt)
                    logger.warning(
                        "%s (attempt %d/%d). Waiting %.0fs...",
                        "Rate limited" if is_rate_limit else f"API error: {e}",
                        attempt + 1,
                        self._max_retries,
                        delay,
                    )
                    time.sleep(delay)
                else:
                    raise

        return ""
