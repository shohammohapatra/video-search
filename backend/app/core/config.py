from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Natural Language Video Search"
    api_prefix: str = "/api"
    database_url: str = "sqlite:///./dev.db"
    sync_database_url: str | None = None
    redis_url: str = "redis://redis:6379/0"
    storage_path: Path = Path("./storage")
    max_upload_size: int = 1024 * 1024 * 1024
    allowed_video_extensions: set[str] = {".mp4", ".mov", ".mkv", ".webm"}
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    llm_provider: str = "local"
    llm_api_key: str | None = None
    model_name: str = "local-grounded"
    embedding_provider: str = "local"
    embedding_api_key: str | None = None
    embedding_model: str = "hashing-384"
    embedding_dimensions: int = 384
    speech_provider: str = "local"
    whisper_model: str = "base"
    vision_provider: str = "local"
    vision_model: str = "gpt-4o-mini"
    ollama_base_url: str = "http://host.docker.internal:11434"
    ocr_provider: str = "local"
    frame_sample_seconds: float = 10.0
    scene_threshold: float = 18.0
    chunk_seconds: float = 30.0
    retrieval_top_k: int = 8

    # Prefer one combined stream so downloads do not depend on YouTube's separate-stream challenge.
    youtube_download_format: str = "bestvideo[height<=720][vcodec^=avc1]+bestaudio[acodec^=mp4a]/best[height<=720]"

    @property
    def effective_database_url(self) -> str:
        return self.sync_database_url or self.database_url


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.storage_path.mkdir(parents=True, exist_ok=True)
    (settings.storage_path / "videos").mkdir(parents=True, exist_ok=True)
    (settings.storage_path / "audio").mkdir(parents=True, exist_ok=True)
    (settings.storage_path / "frames").mkdir(parents=True, exist_ok=True)
    return settings


settings = get_settings()
