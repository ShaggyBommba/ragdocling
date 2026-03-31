from pydantic_settings import BaseSettings, SettingsConfigDict


class LoggingSettings(BaseSettings):
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_json: bool = False
    log_dir: str | None = None
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


class AppSettings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/dacke"
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend_url: str = "redis://localhost:6379/1"
    embedder_base_url: str = "http://localhost:1234"
    qdrant_url: str = "http://localhost:6333"
    logging: LoggingSettings = LoggingSettings()
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
