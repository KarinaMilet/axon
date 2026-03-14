from __future__ import annotations

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Send a prompt and return the raw text response."""
        ...

    @abstractmethod
    def generate_json(self, prompt: str, schema: dict | None = None) -> dict:
        """Send a prompt expecting a JSON response and return parsed dict."""
        ...
