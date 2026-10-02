from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str
    log_level: str = "INFO"
    mini_app_url: str | None = None
    ai_enabled: bool = False
    openai_api_key: str | None = None
    openai_model: str = "gpt-5.6-luna"
    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    twilio_api_key_sid: str | None = None
    twilio_api_key_secret: str | None = None
    twilio_voice_app_sid: str | None = None
    twilio_voice_from_number: str | None = None
    public_base_url: str | None = None
    location_db_path: str = "/app/data/aliali_location.db"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
