from __future__ import annotations

from axon.llm.base import LLMProvider


def create_provider(config: dict) -> LLMProvider:
    """Factory: instantiate the LLM provider specified in config."""
    provider_name = config.get("llm", {}).get("provider", "gemini")

    if provider_name == "gemini":
        from axon.llm.gemini import GeminiProvider

        return GeminiProvider(config)
    elif provider_name == "ollama":
        from axon.llm.ollama import OllamaProvider

        return OllamaProvider(config)
    elif provider_name == "gpt":
        from axon.llm.gpt import GPTProvider

        return GPTProvider(config)
    else:
        raise ValueError(f"Unknown LLM provider: {provider_name}")


__all__ = ["LLMProvider", "create_provider"]
