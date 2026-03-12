from __future__ import annotations

import json
import logging

import requests

from axon.llm.base import LLMProvider

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    def __init__(self, config: dict):
        llm_cfg = config["llm"]
        self._base_url = llm_cfg.get("ollama_base_url", "http://localhost:11434")
        self._model = llm_cfg.get("model", "qwen2.5:14b")
        self._temperature = llm_cfg.get("temperature", 0.2)
        self._max_tokens = llm_cfg.get("max_tokens", 1024)

    def generate(self, prompt: str) -> str:
        resp = requests.post(
            f"{self._base_url}/api/generate",
            json={
                "model": self._model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": self._temperature,
                    "num_predict": self._max_tokens,
                },
            },
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()["response"]

    def generate_json(self, prompt: str) -> dict:
        text = self.generate(prompt).strip()

        if text.startswith("```"):
            lines = text.split("\n")
            lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            retry_prompt = prompt + "\n\nIMPORTANT: Return ONLY valid JSON, no markdown fences."
            text = self.generate(retry_prompt).strip()
            if text.startswith("```"):
                lines = text.split("\n")
                lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                text = "\n".join(lines)
            return json.loads(text)
