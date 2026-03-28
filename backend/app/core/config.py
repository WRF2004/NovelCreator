from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Novel Creator"
    api_prefix: str = "/api"
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    backend_root: Path = Path(__file__).resolve().parents[2]
    storage_root: Path = backend_root / "storage"
    books_root: Path = storage_root / "books"
    datasets_root: Path = storage_root / "datasets"
    models_root: Path = storage_root / "models"
    db_path: Path = storage_root / "app.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()


def ensure_storage_dirs() -> None:
    settings.storage_root.mkdir(parents=True, exist_ok=True)
    settings.books_root.mkdir(parents=True, exist_ok=True)
    settings.datasets_root.mkdir(parents=True, exist_ok=True)
    settings.models_root.mkdir(parents=True, exist_ok=True)

