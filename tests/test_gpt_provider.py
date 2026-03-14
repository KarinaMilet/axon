from __future__ import annotations

from types import SimpleNamespace

import httpx
import pytest
from openai import APIError, RateLimitError

from axon.llm.gpt import GPTProvider


class FakeResponsesAPI:
    def __init__(self, side_effects: list[object]):
        self._side_effects = list(side_effects)
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        result = self._side_effects.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


class FakeClient:
    def __init__(self, side_effects: list[object]):
        self.responses = FakeResponsesAPI(side_effects)


def _client_factory(side_effects: list[object]):
    def factory(**kwargs):
        return FakeClient(side_effects)

    return factory


def _response(text: str) -> SimpleNamespace:
    return SimpleNamespace(output_text=text)


def _httpx_response(status_code: int) -> httpx.Response:
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    return httpx.Response(status_code, headers={"x-request-id": "req_123"}, request=request)


def test_generate_returns_output_text(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    provider = GPTProvider(
        {"llm": {"provider": "gpt", "model": "gpt-5-mini"}},
        client_factory=_client_factory([_response("plain text")]),
    )

    assert provider.generate("hello") == "plain text"


def test_generate_json_with_schema_uses_json_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    schema = {
        "name": "paper_analysis",
        "schema": {
            "type": "object",
            "properties": {"value": {"type": "string"}},
            "required": ["value"],
            "additionalProperties": False,
        },
    }
    provider = GPTProvider(
        {"llm": {"provider": "gpt"}},
        client_factory=_client_factory([_response('{"value":"ok"}')]),
    )

    data = provider.generate_json("hello", schema=schema)

    assert data == {"value": "ok"}
    assert provider._client.responses.calls[0]["text"]["format"] == {
        "type": "json_schema",
        "name": "paper_analysis",
        "schema": schema["schema"],
        "strict": True,
    }


def test_generate_json_without_schema_uses_json_object(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    provider = GPTProvider(
        {"llm": {"provider": "gpt"}},
        client_factory=_client_factory([_response('{"value":"ok"}')]),
    )

    data = provider.generate_json("hello")

    assert data == {"value": "ok"}
    assert provider._client.responses.calls[0]["text"]["format"] == {"type": "json_object"}
    assert "Return ONLY a valid JSON object" in provider._client.responses.calls[0]["input"]


def test_generate_retries_rate_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    sleep_calls: list[float] = []
    monkeypatch.setattr("axon.llm.gpt.time.sleep", lambda delay: sleep_calls.append(delay))

    provider = GPTProvider(
        {"llm": {"provider": "gpt"}},
        client_factory=_client_factory(
                [
                    RateLimitError("rate limited", response=_httpx_response(429), body=None),
                    _response("plain text"),
                ]
            ),
        )

    assert provider.generate("hello") == "plain text"
    assert sleep_calls == [15.0]


def test_generate_retries_transient_api_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    sleep_calls: list[float] = []
    monkeypatch.setattr("axon.llm.gpt.time.sleep", lambda delay: sleep_calls.append(delay))

    provider = GPTProvider(
        {"llm": {"provider": "gpt"}},
        client_factory=_client_factory(
                [
                    APIError("server error", request=httpx.Request("POST", "https://api.openai.com/v1/responses"), body=None),
                    _response("plain text"),
                ]
            ),
        )

    assert provider.generate("hello") == "plain text"
    assert sleep_calls == [5.0]


def test_missing_api_key_raises_clear_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        GPTProvider({"llm": {"provider": "gpt"}})
