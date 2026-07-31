import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    app_name: str = "GrowthLens API"
    app_version: str = "0.1.0"
    frontend_origins: tuple[str, ...] = (
        "http://localhost:3000",
        "http://127.0.0.1:3000",
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
