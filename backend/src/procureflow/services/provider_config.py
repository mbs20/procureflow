"""Shared transport configuration for document interpretation and narratives."""

from typing import TypedDict
from urllib.parse import urlparse

from procureflow.config import Settings


class ProviderConfigurationError(ValueError):
    """The selected provider cannot run with the supplied configuration."""


class CompletionOptions(TypedDict, total=False):
    model: str
    api_key: str
    api_base: str


def completion_options(settings: Settings) -> CompletionOptions:
    provider = settings.llm_provider
    if provider == "mock":
        raise ProviderConfigurationError("The mock provider does not use a remote transport.")
    if provider == "openai":
        if not settings.openai_api_key or not settings.openai_api_key.strip():
            raise ProviderConfigurationError("Provider 'openai' requires OPENAI_API_KEY.")
        model = settings.openai_model.strip()
        if not model:
            raise ProviderConfigurationError("Provider 'openai' requires OPENAI_MODEL.")
        return {
            "model": f"openai/{model.removeprefix('openai/')}",
            "api_key": settings.openai_api_key,
        }
    if provider == "anthropic":
        if not settings.anthropic_api_key or not settings.anthropic_api_key.strip():
            raise ProviderConfigurationError("Provider 'anthropic' requires ANTHROPIC_API_KEY.")
        model = settings.anthropic_model.strip()
        if not model:
            raise ProviderConfigurationError("Provider 'anthropic' requires ANTHROPIC_MODEL.")
        return {
            "model": f"anthropic/{model.removeprefix('anthropic/')}",
            "api_key": settings.anthropic_api_key,
        }
    if provider == "ollama":
        endpoint = urlparse(settings.ollama_base_url)
        if endpoint.scheme not in ("http", "https") or not endpoint.hostname:
            raise ProviderConfigurationError("Provider 'ollama' requires a valid OLLAMA_BASE_URL.")
        model = settings.ollama_model.strip()
        if not model:
            raise ProviderConfigurationError("Provider 'ollama' requires OLLAMA_MODEL.")
        model = model.removeprefix("ollama/").removeprefix("ollama_chat/")
        return {"model": f"ollama_chat/{model}", "api_base": settings.ollama_base_url.rstrip("/")}
    raise ProviderConfigurationError(f"Unsupported provider: {provider!r}.")
