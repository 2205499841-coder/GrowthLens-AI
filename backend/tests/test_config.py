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
