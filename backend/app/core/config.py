from dataclasses import dataclass


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


settings = Settings()
