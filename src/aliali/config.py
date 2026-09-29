from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str
    log_level: str = "INFO"
    mini_app_url: str | None = None
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
