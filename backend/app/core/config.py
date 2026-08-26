from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
  app_name: str = "Trace"
  app_env: str = "development"
  debug: bool = True
  api_v1_prefix: str = "/api/v1"
  backend_host: str = "0.0.0.0"
  backend_port: int = 8000
  database_url: str
  
  redis_url: str
  celery_broker_url: str
  celery_result_backend: str
  minio_endpoint: str
  minio_access_key: str
  minio_secret_key: str
  minio_bucket: str
  minio_secure: bool = False
  
  jwt_secret_key: str
  jwt_algorithm: str = "HS256"
  access_token_expire_minutes: int = 30
  refresh_token_expire_days: int = 7
  
  password_reset_token_expire_minutes: int = 30
  email_verification_token_expire_hours: int = 24
  max_failed_login_attempts: int = 5
  login_lockout_minutes: int = 15
  login_rate_limit_attempts: int = 10
  login_rate_limit_window_seconds: int = 60
  password_reset_rate_limit_attempts: int = 5
  password_reset_rate_limit_window_seconds: int = 900
  registration_rate_limit_attempts: int = 5
  registration_rate_limit_window_seconds: int = 3600
  
  email_enabled: bool = False
  smtp_host: str = ""
  smtp_port: int = 587
  smtp_username: str = ""
  smtp_password: str = ""
  smtp_from_email: str = ""
  smtp_from_name: str = "Trace"
  smtp_use_tls: bool = True
  
  frontend_base_url: str = "http://localhost:5085"
  ai_enabled: bool = False
  ollama_base_url: str = "http://ollama:11434"
  ollama_model: str = "qwen2.5:7b-instruct"
  default_locale: str = "en"
  supported_locales: str = "en,ur"
  default_currency: str = "PKR"
  default_timezone: str = "Asia/Karachi"
  cors_origins: str = "http://localhost:5085"
  model_config = SettingsConfigDict(
    env_file=".env",
    extra="ignore",
    case_sensitive=False,
  )

  @property
  def cors_origin_list(self) -> list[str]:
    return [
      item.strip()
      for item in self.cors_origins.split(",")
      if item.strip()
    ]

@lru_cache
def get_settings() -> Settings:
  return Settings()

settings = get_settings()