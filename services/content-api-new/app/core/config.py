from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
  database_url: str
  app_env: str = "dev"
  log_level: str = "INFO"
  frontend_origin: str = "http://localhost:3000"

  model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
