"""Provider routing tests use a local transport double; no paid API requests."""

from importlib import import_module
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from procureflow.config import Settings

narrative_module = import_module("procureflow.services.narrative_service")
extraction_module = import_module("procureflow.services.extractors.llm_extractor")


@pytest.fixture
def transport(monkeypatch):
    import instructor

    create = Mock()
    factory = Mock(
        return_value=SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=create))
        )
    )
    monkeypatch.setattr(instructor, "from_litellm", factory)
    return create


def configure(monkeypatch, provider, **kwargs):
    config = Settings(
        _env_file=None,
        PROCUREFLOW_LLM_PROVIDER="mock",
        openai_api_key=None,
        anthropic_api_key=None,
        ollama_base_url="http://localhost:11434",
    )
    config = config.model_copy(update={"llm_provider": provider, **kwargs})
    monkeypatch.setattr(extraction_module, "settings", config)
    monkeypatch.setattr(narrative_module, "settings", config)
    return config


@pytest.mark.parametrize(
    "provider,key,model",
    [
        ("openai", "openai_api_key", "openai/example-model"),
        ("anthropic", "anthropic_api_key", "anthropic/example-model"),
        ("ollama", None, "ollama_chat/example-model"),
    ],
)
def test_selected_provider_reaches_both_transports(monkeypatch, transport, provider, key, model):
    kwargs = {f"{provider}_model": "example-model"}
    if key:
        kwargs[key] = "synthetic-test-credential"
    configure(monkeypatch, provider, **kwargs)
    extracted = extraction_module.LLMExtractedQuotation(line_items=[])
    transport.return_value = extracted
    assert extraction_module.LLMExtractor().extract_from_tagged_chunks([]) is extracted
    assert transport.call_args.kwargs["model"] == model
    if key:
        assert transport.call_args.kwargs["api_key"] == "synthetic-test-credential"
    else:
        assert "api_key" not in transport.call_args.kwargs
        assert transport.call_args.kwargs["api_base"] == "http://localhost:11434"

    service = narrative_module.NarrativeService()
    monkeypatch.setattr(service, "_sections_to_claims", lambda *_: [])
    service._live_generate(SimpleNamespace(context_payload={}), None, "Synthetic context")
    assert transport.call_args.kwargs["model"] == model
    if key:
        assert transport.call_args.kwargs["api_key"] == "synthetic-test-credential"
    else:
        assert transport.call_args.kwargs["api_base"] == "http://localhost:11434"


@pytest.mark.parametrize(
    "provider,expected",
    [
        ("openai", "OPENAI_API_KEY"),
        ("anthropic", "ANTHROPIC_API_KEY"),
        ("unsupported", "Unsupported"),
    ],
)
def test_invalid_configuration_fails_explicitly(monkeypatch, transport, provider, expected):
    configure(monkeypatch, provider)
    with pytest.raises(ValueError, match=expected):
        extraction_module.LLMExtractor().extract_from_tagged_chunks([])
    with pytest.raises(ValueError, match=expected):
        narrative_module.NarrativeService()._live_generate(None, None, "Synthetic context")
    transport.assert_not_called()


def test_mock_is_offline(monkeypatch, transport):
    configure(monkeypatch, "mock")
    result = extraction_module.LLMExtractor().extract_from_tagged_chunks([])
    assert result.line_items == []
    transport.assert_not_called()


def test_remote_failure_does_not_fall_back(monkeypatch, transport):
    configure(monkeypatch, "anthropic", anthropic_api_key="synthetic-test-credential")
    transport.side_effect = RuntimeError("Transport unavailable")
    with pytest.raises(RuntimeError, match="Transport unavailable"):
        extraction_module.LLMExtractor().extract_from_tagged_chunks([])


def test_documented_environment_variables_are_applied(monkeypatch):
    monkeypatch.setenv("PROCUREFLOW_ENV", "production")
    monkeypatch.setenv("PROCUREFLOW_DEBUG", "false")
    monkeypatch.setenv("PROCUREFLOW_SECRET_KEY", "synthetic-configuration-test-secret-32chars")
    monkeypatch.setenv("PROCUREFLOW_API_KEY", "synthetic-configuration-test-key")
    monkeypatch.setenv("PROCUREFLOW_LLM_PROVIDER", "ollama")
    config = Settings(_env_file=None)
    assert config.environment == "production"
    assert config.debug is False
    assert config.api_key == "synthetic-configuration-test-key"
