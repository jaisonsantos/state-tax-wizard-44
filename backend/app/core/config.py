from pydantic_settings import BaseSettings
from typing import Optional

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
    
    class Config:
        env_file = ".env"

settings = Settings()