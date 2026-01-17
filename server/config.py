"""
AutoDocs AI - Configuration Management

Uses pydantic-settings for environment variable management with validation.
"""
from functools import lru_cache
from typing import List
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra fields like NEXT_PUBLIC_* variables
    )
    
    # Application
    app_name: str = "AutoDocs AI"
    app_env: str = "development"
    debug: bool = False
    secret_key: str
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: List[str] = ["http://localhost:3000"]
    
    # Database
    database_url: str
    database_pool_size: int = 5
    database_max_overflow: int = 10
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # Storage (S3-compatible)
    s3_endpoint: str
    s3_public_endpoint: str = ""  # Public URL for presigned URLs (e.g., http://localhost:9000)
    s3_access_key: str
    s3_secret_key: str
    s3_bucket_name: str = "autodocs"
    s3_region: str = "us-east-1"
    
    # JWT Auth
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7
    
    # Celery
    celery_broker_url: str
    celery_result_backend: str
    
    # Email (Optional)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "noreply@autodocs.ai"
    
    # Logging
    log_level: str = "INFO"
    
    # Rate Limiting
    rate_limit_requests_per_minute: int = 100
    
    # File Upload Limits
    max_upload_size_mb: int = 50
    max_rows_per_datasource: int = 50000
    
    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            import json
            return json.loads(v)
        return v
    
    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024
    
    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
