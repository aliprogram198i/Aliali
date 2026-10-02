from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str
    log_level: str = "INFO"
    mini_app_url: str | None = None
    ai_enabled: bool = False
    openai_api_key: str | None = None
    openai_model: str = "gpt-5.6-luna"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
