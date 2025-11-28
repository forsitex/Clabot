from pydantic import BaseModel, Field
from typing import Optional


class AppSettings(BaseModel):
    """Setările aplicației salvate în runtime."""

    # Betfair API
    betfair_app_key: str = Field(default="", description="Betfair Application Key")
    betfair_username: str = Field(default="", description="Betfair Username")
    betfair_password: str = Field(default="", description="Betfair Password")
    betfair_cert_file: Optional[str] = Field(default=None, description="Betfair Certificate filename")
    betfair_key_file: Optional[str] = Field(default=None, description="Betfair Key filename")

    # Google Sheets
    google_sheets_spreadsheet_id: str = Field(default="", description="Google Sheets Spreadsheet ID")
    google_credentials_file: Optional[str] = Field(default=None, description="Google credentials filename")

    # Bot Configuration
    bot_run_hour: int = Field(default=13, ge=0, le=23)
    bot_run_minute: int = Field(default=0, ge=0, le=59)
    initial_stake: float = Field(default=100.0, gt=0)
    max_progression_steps: int = Field(default=7, ge=1, le=20)

    # Status
    betfair_connected: bool = Field(default=False)
    google_sheets_connected: bool = Field(default=False)


class SettingsUpdate(BaseModel):
    """Model pentru actualizarea setărilor."""
    betfair_app_key: Optional[str] = None
    betfair_username: Optional[str] = None
    betfair_password: Optional[str] = None
    google_sheets_spreadsheet_id: Optional[str] = None
    bot_run_hour: Optional[int] = Field(default=None, ge=0, le=23)
    bot_run_minute: Optional[int] = Field(default=None, ge=0, le=59)
    initial_stake: Optional[float] = Field(default=None, gt=0)
    max_progression_steps: Optional[int] = Field(default=None, ge=1, le=20)
