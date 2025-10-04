"""
Configuration management using Pydantic Settings.
"""
from typing import Optional, Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    # Application Configuration
    app_name: str = Field(default="llm-orchestrator", alias="APP_NAME")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    app_env: Literal["development", "production", "testing"] = Field(
        default="development", alias="APP_ENV"
    )
    app_debug: bool = Field(default=False, alias="APP_DEBUG")
    
    # Authentication
    auth_token: str = Field(default="your-secret-token", alias="AUTH_TOKEN")
    
    # Database Configuration
    database_type: Literal["sqlite", "mysql"] = Field(default="sqlite", alias="DATABASE_TYPE")
    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/llm_orchestrator.db",
        alias="DATABASE_URL"
    )
    
    # Redis Configuration
    redis_enabled: bool = Field(default=True, alias="REDIS_ENABLED")
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    redis_cache_ttl: int = Field(default=300, alias="REDIS_CACHE_TTL")
    
    # Logging Configuration
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_file: str = Field(default="./logs/app.log", alias="LOG_FILE")
    log_format: Literal["json", "text"] = Field(default="json", alias="LOG_FORMAT")
    
    # Health Check Configuration
    health_check_enabled: bool = Field(default=True, alias="HEALTH_CHECK_ENABLED")
    health_check_interval: int = Field(default=300, alias="HEALTH_CHECK_INTERVAL")
    health_check_max_errors: int = Field(default=5, alias="HEALTH_CHECK_MAX_ERRORS")
    health_check_retry_hours: int = Field(default=1, alias="HEALTH_CHECK_RETRY_HOURS")
    
    # Request Configuration
    max_retry_count: int = Field(default=3, alias="MAX_RETRY_COUNT")
    request_timeout: int = Field(default=30, alias="REQUEST_TIMEOUT")
    response_timeout: int = Field(default=300, alias="RESPONSE_TIMEOUT")
    
    # API Keys
    api_keys: list[str] = Field(
        default_factory=list,
        description="List of valid API keys for authentication"
    )
    admin_key: str = Field(
        default="admin-secret-key-change-this",
        description="Admin API key for management endpoints"
    )
    
    # Rate Limiting
    enable_rate_limiting: bool = Field(default=False, alias="ENABLE_RATE_LIMITING")
    rate_limit_per_minute: int = Field(default=60, alias="RATE_LIMIT_PER_MINUTE")
    
    # CORS Configuration
    cors_origins: str = Field(default="*", alias="CORS_ORIGINS")
    cors_credentials: bool = Field(default=True, alias="CORS_CREDENTIALS")
    cors_methods: str = Field(default="*", alias="CORS_METHODS")
    cors_headers: str = Field(default="*", alias="CORS_HEADERS")
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.app_env == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.app_env == "development"
    
    @property
    def cors_origins_list(self) -> list[str]:
        """Get CORS origins as a list."""
        if self.cors_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    # Convenience properties matching main.py usage
    @property
    def host(self) -> str:
        """Get host address."""
        return self.app_host
    
    @property
    def port(self) -> int:
        """Get port number."""
        return self.app_port
    
    @property
    def debug(self) -> bool:
        """Get debug mode."""
        return self.app_debug
    
    @property
    def environment(self) -> str:
        """Get environment."""
        return self.app_env
    


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """
    Get settings instance.
    
    Returns:
        Settings instance
    """
    return settings