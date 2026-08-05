from app.core.config import LOCAL_CORS_ORIGINS, Settings, get_cors_origins


def test_cors_origins_default_to_local_development(monkeypatch) -> None:
    monkeypatch.delenv("BACKEND_CORS_ORIGINS", raising=False)

    assert get_cors_origins() == LOCAL_CORS_ORIGINS
    assert Settings().frontend_origins == LOCAL_CORS_ORIGINS


def test_cors_origins_use_environment_allowlist(monkeypatch) -> None:
    monkeypatch.setenv(
        "BACKEND_CORS_ORIGINS",
        " https://growthlens.vercel.app/, http://localhost:3000, "
        "https://growthlens.vercel.app ",
    )

    assert Settings().frontend_origins == (
        "https://growthlens.vercel.app",
        "http://localhost:3000",
    )


def test_blank_cors_origins_fall_back_to_local_development(monkeypatch) -> None:
    monkeypatch.setenv("BACKEND_CORS_ORIGINS", " , ")

    assert Settings().frontend_origins == LOCAL_CORS_ORIGINS


def test_ai_provider_defaults_to_deepseek(monkeypatch) -> None:
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    monkeypatch.delenv("AI_MODEL", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    configured_settings = Settings()

    assert configured_settings.ai_provider == "deepseek"
    assert configured_settings.ai_model == "deepseek-v4-pro"
    assert configured_settings.deepseek_api_key is None


def test_ai_provider_reads_secrets_without_exposing_them(monkeypatch) -> None:
    monkeypatch.setenv("AI_PROVIDER", "openai")
    monkeypatch.setenv("AI_MODEL", "future-openai-model")
    monkeypatch.setenv("OPENAI_API_KEY", "test-secret")

    configured_settings = Settings()

    assert configured_settings.ai_provider == "openai"
    assert configured_settings.ai_model == "future-openai-model"
    assert configured_settings.openai_api_key == "test-secret"
    assert "test-secret" not in repr(configured_settings)
