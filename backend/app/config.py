from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List
from functools import lru_cache


class Settings(BaseSettings):
    # Betfair API
    betfair_app_key: str = Field(default="", description="Betfair Application Key")
    betfair_username: str = Field(default="", description="Betfair Username")
    betfair_password: str = Field(default="", description="Betfair Password")
    betfair_cert_path: str = Field(default="./certs/betfair.crt", description="Path to Betfair SSL Certificate")
    betfair_key_path: str = Field(default="./certs/betfair.key", description="Path to Betfair SSL Key")

    # Google Sheets
    google_sheets_credentials_path: str = Field(
        default="./credentials/google_service_account.json",
        description="Path to Google Service Account JSON"
    )
    google_sheets_spreadsheet_id: str = Field(default="", description="Google Sheets Spreadsheet ID")

    # Bot Configuration
    bot_timezone: str = Field(default="Europe/Bucharest", description="Timezone for bot execution")
    bot_run_hour: int = Field(default=13, ge=0, le=23, description="Hour to run bot (0-23)")
    bot_run_minute: int = Field(default=0, ge=0, le=59, description="Minute to run bot (0-59)")
    bot_initial_stake: float = Field(default=100.0, gt=0, description="Initial stake in RON")
    bot_max_progression_steps: int = Field(default=7, ge=1, le=20, description="Maximum progression steps before stop loss")

    # Server
    api_host: str = Field(default="0.0.0.0", description="API Host")
    api_port: int = Field(default=8000, description="API Port")
    cors_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        description="Comma-separated list of allowed CORS origins"
    )

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
