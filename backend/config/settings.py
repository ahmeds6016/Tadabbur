"""
Configuration settings for Tafsir Simplified backend
Uses Pydantic settings for environment variable management
"""

from typing import Optional, Dict, Any
from pydantic_settings import BaseSettings
from pydantic import Field
import os


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    # Google Cloud settings
    gcp_project_id: str = Field(default="tafsir-simplified", env="GCP_PROJECT_ID")
    gcp_infrastructure_project: str = Field(default="tafsir-simplified", env="GCP_INFRASTRUCTURE_PROJECT")
    location: str = Field(default="us-central1", env="LOCATION")

    # Firestore settings
    firestore_database_id: str = Field(default="(default)", env="FIRESTORE_DATABASE_ID")

    # Redis settings
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    redis_db: int = Field(default=0, env="REDIS_DB")
    redis_ssl: bool = Field(default=False, env="REDIS_SSL")
    redis_connection_timeout: int = Field(default=5, env="REDIS_CONNECTION_TIMEOUT")
    redis_max_connections: int = Field(default=50, env="REDIS_MAX_CONNECTIONS")

    # Cache settings
    cache_redis_ttl: int = Field(default=3600, env="CACHE_REDIS_TTL")  # 1 hour
    cache_firestore_ttl_days: int = Field(default=7, env="CACHE_FIRESTORE_TTL_DAYS")
    cache_compression_threshold: int = Field(default=1024, env="CACHE_COMPRESSION_THRESHOLD")

    # Rate limiting settings
    rate_limit_enabled: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    rate_limit_requests_per_minute: int = Field(default=30, env="RATE_LIMIT_REQUESTS_PER_MINUTE")
    rate_limit_requests_per_hour: int = Field(default=500, env="RATE_LIMIT_REQUESTS_PER_HOUR")
    rate_limit_requests_per_day: int = Field(default=2000, env="RATE_LIMIT_REQUESTS_PER_DAY")

    # Gemini settings
    gemini_model_id: str = Field(default="gemini-2.0-pro", env="GEMINI_MODEL_ID")
    gemini_temperature: float = Field(default=0.3, env="GEMINI_TEMPERATURE")
    gemini_max_output_tokens: int = Field(default=65536, env="GEMINI_MAX_OUTPUT_TOKENS")
    gemini_timeout: int = Field(default=120, env="GEMINI_TIMEOUT")

    # Application settings
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    cors_origins: str = Field(default="*", env="CORS_ORIGINS")
    max_verse_limit: int = Field(default=50, env="MAX_VERSE_LIMIT")
    batch_query_size: int = Field(default=10, env="BATCH_QUERY_SIZE")

    # Performance settings
    thread_pool_size: int = Field(default=10, env="THREAD_POOL_SIZE")
    connection_pool_size: int = Field(default=20, env="CONNECTION_POOL_SIZE")
    request_timeout: int = Field(default=30, env="REQUEST_TIMEOUT")

    # Feature flags
    enable_batch_queries: bool = Field(default=True, env="ENABLE_BATCH_QUERIES")
    enable_redis_cache: bool = Field(default=True, env="ENABLE_REDIS_CACHE")
    enable_performance_monitoring: bool = Field(default=True, env="ENABLE_PERFORMANCE_MONITORING")
    enable_verse_prefetch: bool = Field(default=True, env="ENABLE_VERSE_PREFETCH")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    def get_redis_url(self) -> str:
        """Get Redis connection URL"""
        if self.redis_password:
            auth = f":{self.redis_password}@"
        else:
            auth = ""

        protocol = "rediss" if self.redis_ssl else "redis"
        return f"{protocol}://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"

    def get_cors_origins_list(self) -> list:
        """Get CORS origins as list"""
        if self.cors_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return not self.debug and os.getenv("ENVIRONMENT", "").lower() == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.debug or os.getenv("ENVIRONMENT", "").lower() in ["development", "dev"]

    def get_tier_limits(self, tier: str = "free") -> Dict[str, int]:
        """Get rate limits for a specific tier"""
        tier_configs = {
            "free": {
                "requests_per_minute": 20,
                "requests_per_hour": 300,
                "requests_per_day": 1000
            },
            "premium": {
                "requests_per_minute": 60,
                "requests_per_hour": 1000,
                "requests_per_day": 5000
            },
            "unlimited": {
                "requests_per_minute": 1000,
                "requests_per_hour": 10000,
                "requests_per_day": 100000
            }
        }
        return tier_configs.get(tier, tier_configs["free"])


# Create global settings instance
settings = Settings()


# Persona configuration (5 consolidated personas)
PERSONA_CONFIGS = {
    "new_revert": {
        "verse_limit": 5,
        "format_style": "beginner_friendly",
        "include_transliteration": True,
        "simplify_language": True
    },
    "curious_explorer": {
        "verse_limit": 7,
        "format_style": "balanced",
        "include_transliteration": True,
        "simplify_language": False
    },
    "practicing_muslim": {
        "verse_limit": 8,
        "format_style": "balanced",
        "include_transliteration": False,
        "simplify_language": False
    },
    "student": {
        "verse_limit": 10,
        "format_style": "academic",
        "include_transliteration": False,
        "simplify_language": False
    },
    "advanced_learner": {
        "verse_limit": 15,
        "format_style": "scholarly",
        "include_transliteration": False,
        "simplify_language": False
    }
}


# Quran metadata (for validation)
QURAN_METADATA = {
    1: {"name": "Al-Fatihah", "verses": 7, "type": "Meccan"},
    2: {"name": "Al-Baqarah", "verses": 286, "type": "Medinan"},
    3: {"name": "Al-Imran", "verses": 200, "type": "Medinan"},
    # ... Add all 114 surahs
}


# Common verse references (for prefetching)
COMMON_VERSE_REFS = [
    "1:1-7",    # Al-Fatihah
    "2:255",    # Ayatul Kursi
    "2:256",    # No compulsion
    "2:186",    # I am near
    "39:53",    # Allah's mercy
    "112:1-4",  # Al-Ikhlas
    "24:35",    # Light verse
    "67:1-2",   # Life and death
    "51:56",    # Created to worship
    "3:185",    # Every soul shall taste death
]