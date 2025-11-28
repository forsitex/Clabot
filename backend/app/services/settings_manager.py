import json
import logging
from pathlib import Path
from typing import Optional

from app.models.settings import AppSettings, SettingsUpdate

logger = logging.getLogger(__name__)


class SettingsManager:
    """Manager pentru setările aplicației cu persistență în fișier JSON."""

    def __init__(self):
        self._settings = AppSettings()
        self._settings_file = Path(__file__).parent.parent.parent / "data" / "settings.json"
        self._ensure_data_dir()
        self._load_settings()

    def _ensure_data_dir(self) -> None:
        """Creează directorul data dacă nu există."""
        data_dir = self._settings_file.parent
        data_dir.mkdir(parents=True, exist_ok=True)

    def _load_settings(self) -> None:
        """Încarcă setările din fișier."""
        if self._settings_file.exists():
            try:
                with open(self._settings_file, "r") as f:
                    data = json.load(f)
                    self._settings = AppSettings(**data)
                    logger.info("Setări încărcate din fișier")
            except Exception as e:
                logger.error(f"Eroare la încărcarea setărilor: {e}")
                self._settings = AppSettings()
        else:
            logger.info("Fișier setări nu există, folosesc valori implicite")

    def _save_settings(self) -> bool:
        """Salvează setările în fișier."""
        try:
            with open(self._settings_file, "w") as f:
                json.dump(self._settings.model_dump(), f, indent=2)
            logger.info("Setări salvate în fișier")
            return True
        except Exception as e:
            logger.error(f"Eroare la salvarea setărilor: {e}")
            return False

    def get_settings(self) -> AppSettings:
        """Returnează setările curente."""
        return self._settings

    def update_settings(self, updates: SettingsUpdate) -> AppSettings:
        """Actualizează setările."""
        update_data = updates.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            if hasattr(self._settings, key) and value is not None:
                setattr(self._settings, key, value)

        self._save_settings()
        return self._settings

    def get_betfair_credentials(self) -> dict:
        """Returnează credențialele Betfair."""
        return {
            "app_key": self._settings.betfair_app_key,
            "username": self._settings.betfair_username,
            "password": self._settings.betfair_password,
            "cert_file": self._settings.betfair_cert_file,
            "key_file": self._settings.betfair_key_file
        }

    def get_google_sheets_config(self) -> dict:
        """Returnează configurația Google Sheets."""
        return {
            "spreadsheet_id": self._settings.google_sheets_spreadsheet_id,
            "credentials_file": self._settings.google_credentials_file
        }

    def get_bot_config(self) -> dict:
        """Returnează configurația botului."""
        return {
            "run_hour": self._settings.bot_run_hour,
            "run_minute": self._settings.bot_run_minute,
            "initial_stake": self._settings.initial_stake,
            "max_progression_steps": self._settings.max_progression_steps
        }

    def set_betfair_connected(self, connected: bool) -> None:
        """Setează statusul conexiunii Betfair."""
        self._settings.betfair_connected = connected
        self._save_settings()

    def set_google_sheets_connected(self, connected: bool) -> None:
        """Setează statusul conexiunii Google Sheets."""
        self._settings.google_sheets_connected = connected
        self._save_settings()

    def is_betfair_configured(self) -> bool:
        """Verifică dacă Betfair este configurat."""
        return bool(
            self._settings.betfair_app_key and
            self._settings.betfair_username and
            self._settings.betfair_password
        )

    def is_google_sheets_configured(self) -> bool:
        """Verifică dacă Google Sheets este configurat."""
        return bool(self._settings.google_sheets_spreadsheet_id)


settings_manager = SettingsManager()
