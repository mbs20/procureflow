import pytest
from pydantic import ValidationError

from procureflow.config import Settings


class TestProductionConfigurationGuardrails:
    def test_production_rejects_debug_true(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PROCUREFLOW_LLM_PROVIDER", "openai")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        with pytest.raises(ValidationError, match="PROCUREFLOW_DEBUG must be False in production"):
            Settings(
                environment="production",
                debug=True,
                secret_key="a_valid_production_secret_key_that_is_long_enough",
                api_key="a_valid_custom_prod_api_key_12345",
            )

    def test_production_rejects_default_dev_secret(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PROCUREFLOW_LLM_PROVIDER", "openai")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        with pytest.raises(ValidationError, match="A secure SECRET_KEY of at least 32 characters is required in production"):
            Settings(
                environment="production",
                debug=False,
                secret_key="dev_secret_key_change_in_production_32chars_min",
                api_key="a_valid_custom_prod_api_key_12345",
            )

    def test_production_rejects_short_secret(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PROCUREFLOW_LLM_PROVIDER", "openai")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        with pytest.raises(ValidationError, match="A secure SECRET_KEY of at least 32 characters is required in production"):
            Settings(
                environment="production",
                debug=False,
                secret_key="short_secret",
                api_key="a_valid_custom_prod_api_key_12345",
            )

    def test_production_rejects_default_dev_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PROCUREFLOW_LLM_PROVIDER", "openai")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        with pytest.raises(ValidationError, match="PROCUREFLOW_API_KEY must be changed from the default development key in production"):
            Settings(
                environment="production",
                debug=False,
                secret_key="a_valid_production_secret_key_that_is_long_enough",
                api_key="procureflow_dev_api_key_12345",
            )

    def test_production_rejects_wildcard_cors(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PROCUREFLOW_LLM_PROVIDER", "openai")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        with pytest.raises(ValidationError, match="Wildcard CORS origins"):
            Settings(
                environment="production",
                debug=False,
                secret_key="a_valid_production_secret_key_that_is_long_enough",
                api_key="a_valid_custom_prod_api_key_12345",
                cors_origins=["https://procureflow.example.com", "*"],
            )

    def test_production_rejects_mock_llm(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PROCUREFLOW_LLM_PROVIDER", "mock")
        with pytest.raises(ValidationError, match="PROCUREFLOW_LLM_PROVIDER='mock' is only permitted in development and test environments"):
            Settings(
                environment="production",
                debug=False,
                secret_key="a_valid_production_secret_key_that_is_long_enough",
                api_key="a_valid_custom_prod_api_key_12345",
            )

    def test_production_valid_configuration_passes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PROCUREFLOW_LLM_PROVIDER", "openai")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        s = Settings(
            environment="production",
            debug=False,
            secret_key="a_valid_production_secret_key_that_is_long_enough_32",
            api_key="prod_custom_api_key_998877",
            cors_origins=["https://app.procureflow.example.com"],
        )
        assert s.environment == "production"
        assert s.debug is False
        assert s.api_key == "prod_custom_api_key_998877"
