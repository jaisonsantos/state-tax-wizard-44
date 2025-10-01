from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://user:pass@postgres:5432/rdf"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24 hours
    app_env: str = "dev"
    stripe_public_key: Optional[str] = "pk_test_stub"
    stripe_secret_key: Optional[str] = "sk_test_stub"
    shopify_app_key: Optional[str] = "stub_key"
    shopify_app_secret: Optional[str] = "stub_secret"
    hmac_max_skew_seconds: int = 300
    hmac_replay_ttl_seconds: int = 600
    redis_url: Optional[str] = None
    rate_limit_window_seconds: int = 60
    rate_limit_limit: int = 120
    
    class Config:
        env_file = ".env"


settings = Settings()
