from __future__ import annotations

import pytest

from axon.llm import create_provider
from axon.llm.gpt import GPTProvider


def test_create_provider_supports_gpt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    provider = create_provider({"llm": {"provider": "gpt"}})
    assert isinstance(provider, GPTProvider)


def test_create_provider_rejects_unknown_provider() -> None:
    with pytest.raises(ValueError, match="Unknown LLM provider"):
        create_provider({"llm": {"provider": "unknown"}})
