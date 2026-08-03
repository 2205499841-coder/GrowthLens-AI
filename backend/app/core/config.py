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


@dataclass(frozen=True)
class Settings:
    app_name: str = "GrowthLens API"
    app_version: str = "0.1.0"
    frontend_origins: tuple[str, ...] = field(
        default_factory=get_cors_origins,
    )
    max_upload_size_bytes: int = 10 * 1024 * 1024
    preview_row_limit: int = 10
    ai_report_provider: str = os.getenv(
        "AI_REPORT_PROVIDER",
        "mock",
    ).strip().lower()
    openai_api_key: str | None = field(
        default=os.getenv("OPENAI_API_KEY"),
        repr=False,
    )
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-5.6")


settings = Settings()
