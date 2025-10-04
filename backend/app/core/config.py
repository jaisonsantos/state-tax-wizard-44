from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://user:pass@postgres:5432/rdf"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24 hours
    app_env: str = "dev"
    stripe_public_key: Optional[str] = "pk_test_stub"
    stripe_secret_key: Optional[str] = None
    stripe_webhook_secret: Optional[str] = None
    stripe_price_id_starter: Optional[str] = None
    stripe_price_id_pro: Optional[str] = None
    stripe_price_id_plus: Optional[str] = None
    shopify_app_key: Optional[str] = "stub_key"
    shopify_app_secret: Optional[str] = "stub_secret"
    integrations_woo_enabled: bool = False
    integrations_shopify_enabled: bool = False
    hmac_max_skew_seconds: int = 300
    hmac_replay_ttl_seconds: int = 600
    redis_url: Optional[str] = None
    rate_limit_window_seconds: int = 60
    rate_limit_limit: int = 120
    vite_api_base_url: Optional[str] = None
    smoke_hmac_secret: Optional[str] = "demo-hmac-secret"


settings = Settings()
