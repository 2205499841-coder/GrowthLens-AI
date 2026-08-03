import os
from dataclasses import dataclass, field


LOCAL_CORS_ORIGINS = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
)


def get_cors_origins() -> tuple[str, ...]:
    """Read and normalize the comma-separated CORS origin allowlist."""
    configured_origins = os.getenv("BACKEND_CORS_ORIGINS", "")
    if not configured_origins.strip():
        return LOCAL_CORS_ORIGINS

    origins: list[str] = []
    for value in configured_origins.split(","):
        origin = value.strip().rstrip("/")
        if origin and origin not in origins:
            origins.append(origin)

    return tuple(origins) or LOCAL_CORS_ORIGINS


def get_optional_secret(name: str) -> str | None:
    value = os.getenv(name, "").strip()
    return value or None


@dataclass(frozen=True)
class Settings:
    app_name: str = "GrowthLens API"
    app_version: str = "0.1.0"
    frontend_origins: tuple[str, ...] = field(
        default_factory=get_cors_origins,
    )
    max_upload_size_bytes: int = 10 * 1024 * 1024
    preview_row_limit: int = 10
    ai_provider: str = field(
        default_factory=lambda: os.getenv(
            "AI_PROVIDER",
            "deepseek",
        ).strip().lower()
    )
    deepseek_api_key: str | None = field(
        default_factory=lambda: get_optional_secret("DEEPSEEK_API_KEY"),
        repr=False,
    )
    ai_model: str = field(
        default_factory=lambda: os.getenv(
            "AI_MODEL",
            "deepseek-chat",
        ).strip()
    )
    openai_api_key: str | None = field(
        default_factory=lambda: get_optional_secret("OPENAI_API_KEY"),
        repr=False,
    )


settings = Settings()
