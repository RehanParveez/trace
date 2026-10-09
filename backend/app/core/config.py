from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from dotenv import load_dotenv
from pathlib import Path

_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_env_path)

class Settings(BaseSettings):
  app_name: str = "Trace"
  app_env: str = "development"
  debug: bool = True
  api_v1_prefix: str = "/api/v1"
  backend_host: str = "0.0.0.0"
  backend_port: int = 8015
  database_url: str
  migrations_database_url: str
  
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
  
  idempotency_key_ttl_seconds: int = 86400
  
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
  rate_limit_auth_per_minute: int = 10
  rate_limit_ai_per_org_per_minute: int = 20
  rate_limit_webhook_per_minute: int = 120
  export_time_limit_seconds: int = 300
  export_soft_time_limit_seconds: int = 270
  calc_max_concurrent_runs_per_org: int = 3
  calc_run_rate_limit_per_minute: int = 5
  export_async_item_threshold: int = 500
  export_retention_days: int = 7
  
  email_enabled: bool = False
  smtp_host: str = ""
  smtp_port: int = 587
  smtp_username: str = ""
  smtp_password: str = ""
  smtp_from_email: str = ""
  smtp_from_name: str = "Trace"
  smtp_use_tls: bool = True
  
  whatsapp_app_secret: str = ""
  whatsapp_webhook_verify_token: str = ""
  whatsapp_media_download_timeout_seconds: int = 240
  whatsapp_graph_api_version: str = "v21.0"
  whatsapp_max_photo_bytes: int = 10 * 1024 * 1024
  minio_public_endpoint: str = ""
  minio_public_secure: bool | None = None
  site_photo_url_ttl_seconds: int = 6 * 60 * 60
  
  ai_provider: str = "ollama"
  ai_api_key: str = ""
  ai_model: str = "claude-haiku-4-5-20251001"
  
  engine_v2_org_ids: str = ""
  engine_default_convention: str = "FRAME_MONOLITHIC_A"

  calc_max_concurrent_runs_per_org: int = 3
  calc_run_rate_limit_per_minute: int = 5
  calc_run_rate_limit_per_hour: int = 30
  calc_time_limit_seconds: int = 1800
  calc_soft_time_limit_seconds: int = 1500
  calc_memory_budget_mb: int = 1536
  calc_worker_max_memory_kb: int = 2_000_000
  calc_heartbeat_seconds: int = 30
  calc_stale_heartbeat_seconds: int = 600
  calc_queued_requeue_seconds: int = 900
  calc_max_attempts: int = 3
  calc_incremental_enabled: bool = True
  calc_incremental_max_change_ratio: float = 0.5
  calc_verify_sample_rate: float = 0.0
  calc_state_keep_runs: int = 2
  calc_staging_retention_days: int = 7
  calc_stage_chunk_rows: int = 5000
  calc_element_fetch_rows: int = 2000
  calc_read_cache_ttl_seconds: int = 3600
  bim_parsing_time_limit_seconds: int = 900
  bim_parsing_soft_time_limit_seconds: int = 780
  bim_element_insert_chunk: int = 1000
  export_async_item_threshold: int = 1500
  export_time_limit_seconds: int = 900
  export_soft_time_limit_seconds: int = 780
  export_retention_days: int = 14
  
  frontend_base_url: str = "http://localhost:5094"
  ai_enabled: bool = False
  ollama_base_url: str = "http://ollama:11434"
  ollama_model: str = "qwen2.5:7b-instruct"
  default_locale: str = "en"
  supported_locales: str = "en,ur"
  default_currency: str = "PKR"
  default_timezone: str = "Asia/Karachi"
  cors_origins: str = "http://localhost:5094"
  model_config = SettingsConfigDict(
    env_file=str(_env_path),
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