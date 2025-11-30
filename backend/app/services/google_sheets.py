import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class GoogleSheetsClient:
    """
    Client pentru Google Sheets API.
    Gestionează persistența datelor: echipe, pariuri, configurări.
    """

    def __init__(self):
        self._client = None
        self._spreadsheet = None
        self._spreadsheet_id: Optional[str] = None
        self._credentials_path: Optional[str] = None
        self._connected = False

    def configure(self, spreadsheet_id: str, credentials_path: Optional[str] = None) -> bool:
        """
        Configurează clientul Google Sheets.

        Args:
            spreadsheet_id: ID-ul spreadsheet-ului
            credentials_path: Calea către fișierul JSON cu credențiale

        Returns:
            True dacă configurarea a reușit
        """
        self._spreadsheet_id = spreadsheet_id
        self._credentials_path = credentials_path
        return True

    def connect(self) -> bool:
        """
        Conectează la Google Sheets API.

        Returns:
            True dacă conexiunea a reușit
        """
        if not self._spreadsheet_id:
            logger.error("Spreadsheet ID nu este configurat")
            return False

        try:
            import gspread
            from google.oauth2.service_account import Credentials

            scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]

            if self._credentials_path:
                credentials = Credentials.from_service_account_file(
                    self._credentials_path,
                    scopes=scopes
                )
            else:
                credentials = Credentials.from_service_account_info(
                    self._get_credentials_from_env(),
                    scopes=scopes
                )

            self._client = gspread.authorize(credentials)
            self._spreadsheet = self._client.open_by_key(self._spreadsheet_id)
            self._connected = True

            logger.info(f"Conectat la Google Sheets: {self._spreadsheet.title}")
            return True

        except Exception as e:
            logger.error(f"Eroare la conectarea la Google Sheets: {e}")
            self._connected = False
            return False

    def _get_credentials_from_env(self) -> dict:
        """Obține credențialele din variabilele de environment."""
        import os
        import json
        import base64

        # Try base64 encoded credentials first
        creds_base64 = os.environ.get("GOOGLE_SHEETS_CREDENTIALS_BASE64", "")
        if creds_base64:
            try:
                creds_json = base64.b64decode(creds_base64).decode('utf-8')
                logger.info("Google Sheets credentials loaded from base64")
                return json.loads(creds_json)
            except Exception as e:
                logger.error(f"Error decoding base64 credentials: {e}")

        # Fallback to JSON string
        creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON", "{}")
        return json.loads(creds_json)

    def is_connected(self) -> bool:
        """Verifică dacă clientul este conectat."""
        return self._connected

    def disconnect(self) -> None:
        """Deconectează clientul."""
        self._client = None
        self._spreadsheet = None
        self._connected = False
        logger.info("Deconectat de la Google Sheets")

    def _get_or_create_worksheet(self, name: str, headers: List[str]) -> Any:
        """Obține sau creează un worksheet."""
        try:
            worksheet = self._spreadsheet.worksheet(name)
        except Exception:
            worksheet = self._spreadsheet.add_worksheet(title=name, rows=1000, cols=len(headers))
            worksheet.append_row(headers)
            logger.info(f"Worksheet creat: {name}")
        return worksheet

    def load_teams(self) -> List[Dict[str, Any]]:
        """
        Încarcă echipele din Google Sheets.

        Returns:
            Lista de echipe ca dicționare
        """
        if not self._connected:
            logger.warning("Nu sunt conectat la Google Sheets")
            return []

        try:
            headers = ["id", "name", "betfair_id", "sport", "league", "country",
                      "cumulative_loss", "last_stake", "progression_step", "status",
                      "created_at", "updated_at", "initial_stake"]
            worksheet = self._get_or_create_worksheet("Index", headers)

            records = worksheet.get_all_records()
            teams = []

            for record in records:
                if record.get("id"):
                    teams.append({
                        "id": str(record["id"]),
                        "name": record.get("name", ""),
                        "betfair_id": record.get("betfair_id") or None,
                        "sport": record.get("sport", "football"),
                        "league": record.get("league", ""),
                        "country": record.get("country", ""),
                        "cumulative_loss": float(record.get("cumulative_loss", 0)),
                        "last_stake": float(record.get("last_stake", 0)),
                        "progression_step": int(record.get("progression_step", 0)),
                        "status": record.get("status", "active"),
                        "created_at": record.get("created_at", datetime.utcnow().isoformat()),
                        "updated_at": record.get("updated_at", datetime.utcnow().isoformat()),
                        "initial_stake": float(record.get("initial_stake", 5))  # Miză inițială per echipă
                    })

            logger.info(f"Încărcate {len(teams)} echipe din Google Sheets")
            return teams

        except Exception as e:
            logger.error(f"Eroare la încărcarea echipelor: {e}")
            return []

    def save_team(self, team: Dict[str, Any]) -> bool:
        """
        Salvează sau actualizează o echipă în Google Sheets.
        Creează și un sheet separat pentru echipă.

        Args:
            team: Datele echipei

        Returns:
            True dacă salvarea a reușit
        """
        if not self._connected:
            logger.warning("Nu sunt conectat la Google Sheets")
            return False

        try:
            # Save to Index sheet
            headers = ["id", "name", "betfair_id", "sport", "league", "country",
                      "cumulative_loss", "last_stake", "progression_step", "status",
                      "created_at", "updated_at", "initial_stake"]
            worksheet = self._get_or_create_worksheet("Index", headers)

            cell = worksheet.find(team["id"])

            row_data = [
                team["id"],
                team["name"],
                team.get("betfair_id", ""),
                team.get("sport", "football"),
                team.get("league", ""),
                team.get("country", ""),
                team.get("cumulative_loss", 0),
                team.get("last_stake", 0),  # 0 până la primul pariu
                team.get("progression_step", 0),
                team.get("status", "active"),
                team.get("created_at", datetime.utcnow().isoformat()),
                datetime.utcnow().isoformat(),
                team.get("initial_stake", 5)  # Miză inițială per echipă
            ]

            if cell:
                row_num = cell.row
                worksheet.update(f"A{row_num}:M{row_num}", [row_data])
            else:
                worksheet.append_row(row_data)

            # Create separate sheet for team
            self._create_team_sheet(team["name"])

            logger.info(f"Echipă salvată: {team['name']}")
            return True

        except Exception as e:
            logger.error(f"Eroare la salvarea echipei: {e}")
            return False

    def _create_team_sheet(self, team_name: str) -> Any:
        """Creează un sheet separat pentru o echipă."""
        try:
            try:
                worksheet = self._spreadsheet.worksheet(team_name)
                logger.info(f"Sheet '{team_name}' există deja")
                self._apply_status_formatting(worksheet)
                return worksheet
            except:
                pass

            headers = ["Data", "Meci", "Competiție", "Cotă", "Miză", "Status", "Profit", "Bet ID"]
            worksheet = self._spreadsheet.add_worksheet(title=team_name, rows=100, cols=len(headers))
            worksheet.append_row(headers)
            self._apply_status_formatting(worksheet)

            logger.info(f"Sheet creat pentru echipa: {team_name}")
            return worksheet

        except Exception as e:
            logger.error(f"Eroare la crearea sheet-ului pentru {team_name}: {e}")
            return None

    def _apply_status_formatting(self, worksheet) -> bool:
        """Aplică conditional formatting pentru coloana Status (F)."""
        try:
            from gspread_formatting import (
                ConditionalFormatRule, BooleanRule, BooleanCondition,
                CellFormat, Color, ConditionalFormatRules, TextFormat, GridRange
            )

            rules = ConditionalFormatRules(worksheet)
            rules.clear()

            range_f = GridRange.from_a1_range("F2:F1000", worksheet)

            won_rule = ConditionalFormatRule(
                ranges=[range_f],
                booleanRule=BooleanRule(
                    condition=BooleanCondition("TEXT_EQ", ["WON"]),
                    format=CellFormat(
                        backgroundColor=Color(0.7, 0.9, 0.7),
                        textFormat=TextFormat(foregroundColor=Color(0.1, 0.5, 0.1), bold=True)
                    )
                )
            )

            lost_rule = ConditionalFormatRule(
                ranges=[range_f],
                booleanRule=BooleanRule(
                    condition=BooleanCondition("TEXT_EQ", ["LOST"]),
                    format=CellFormat(
                        backgroundColor=Color(0.95, 0.7, 0.7),
                        textFormat=TextFormat(foregroundColor=Color(0.7, 0.1, 0.1), bold=True)
                    )
                )
            )

            pending_rule = ConditionalFormatRule(
                ranges=[range_f],
                booleanRule=BooleanRule(
                    condition=BooleanCondition("TEXT_EQ", ["PENDING"]),
                    format=CellFormat(
                        backgroundColor=Color(0.7, 0.85, 0.95),
                        textFormat=TextFormat(foregroundColor=Color(0.1, 0.3, 0.6), bold=True)
                    )
                )
            )

            programat_rule = ConditionalFormatRule(
                ranges=[range_f],
                booleanRule=BooleanRule(
                    condition=BooleanCondition("TEXT_EQ", ["PROGRAMAT"]),
                    format=CellFormat(
                        backgroundColor=Color(0.85, 0.85, 0.85),
                        textFormat=TextFormat(foregroundColor=Color(0.4, 0.4, 0.4), bold=False)
                    )
                )
            )

            rules.append(won_rule)
            rules.append(lost_rule)
            rules.append(pending_rule)
            rules.append(programat_rule)
            rules.save()

            logger.info(f"Conditional formatting aplicat pentru {worksheet.title}")
            return True

        except ImportError as e:
            logger.warning(f"gspread_formatting import error: {e}")
            return False
        except Exception as e:
            logger.error(f"Eroare la aplicarea formatting-ului: {e}")
            return False

    def apply_formatting_to_all_teams(self) -> int:
        """Aplică conditional formatting pe toate sheet-urile echipelor existente."""
        if not self._connected:
            self.connect()

        if not self._connected:
            return 0

        count = 0
        try:
            all_sheets = self._spreadsheet.worksheets()
            for sheet in all_sheets:
                if sheet.title in ["Index", "Istoric"]:
                    continue
                if self._apply_status_formatting(sheet):
                    count += 1
            logger.info(f"Formatting aplicat pe {count} sheet-uri")
        except Exception as e:
            logger.error(f"Eroare la aplicarea formatting-ului global: {e}")
        return count

    def save_matches_for_team(self, team_name: str, matches: List[Dict[str, Any]]) -> bool:
        """
        Salvează meciurile programate în sheet-ul echipei.

        Args:
            team_name: Numele echipei
            matches: Lista de meciuri de salvat

        Returns:
            True dacă salvarea a reușit
        """
        if not self._connected:
            return False

        try:
            worksheet = self._spreadsheet.worksheet(team_name)

            for match in matches:
                # Check if match already exists (by event_name)
                try:
                    cell = worksheet.find(match.get("event_name", ""))
                    if cell:
                        continue  # Skip existing match
                except:
                    pass

                row_data = [
                    match.get("start_time", ""),
                    match.get("event_name", ""),
                    match.get("competition", ""),
                    match.get("odds", ""),
                    "",  # Miză - se completează la plasare
                    "PROGRAMAT",
                    "",  # Profit
                    ""   # Bet ID
                ]
                worksheet.append_row(row_data)

            logger.info(f"Salvate {len(matches)} meciuri pentru {team_name}")
            return True

        except Exception as e:
            logger.error(f"Eroare la salvarea meciurilor pentru {team_name}: {e}")
            return False

    def update_team_progression(self, team_name: str, cumulative_loss: float, step: int, last_stake: float) -> bool:
        """Actualizează progresia în Index sheet."""
        if not self._connected:
            return False

        try:
            worksheet = self._spreadsheet.worksheet("Index")
            cell = worksheet.find(team_name)

            if cell:
                row = cell.row
                worksheet.update_cell(row, 7, cumulative_loss)
                worksheet.update_cell(row, 8, last_stake)
                worksheet.update_cell(row, 9, step)
                worksheet.update_cell(row, 12, datetime.utcnow().isoformat())
                logger.info(f"Progresie actualizată în Index pentru {team_name}")
                return True
            return False
        except Exception as e:
            logger.error(f"Eroare la actualizarea progresiei pentru {team_name}: {e}")
            return False

    def update_team_initial_stake(self, team_name: str, initial_stake: float) -> bool:
        """Actualizează miza inițială pentru o echipă în Index sheet."""
        if not self._connected:
            return False

        try:
            worksheet = self._spreadsheet.worksheet("Index")
            cell = worksheet.find(team_name)

            if cell:
                row = cell.row
                worksheet.update_cell(row, 13, initial_stake)  # Coloana M = initial_stake
                worksheet.update_cell(row, 12, datetime.utcnow().isoformat())  # updated_at
                logger.info(f"Miză inițială actualizată pentru {team_name}: {initial_stake} RON")
                return True
            return False
        except Exception as e:
            logger.error(f"Eroare la actualizarea mizei inițiale pentru {team_name}: {e}")
            return False

    def update_last_stake(self, team_name: str, stake: float) -> bool:
        """Actualizează ultima miză plasată pentru o echipă în Index sheet."""
        if not self._connected:
            return False

        try:
            worksheet = self._spreadsheet.worksheet("Index")
            cell = worksheet.find(team_name)

            if cell:
                row = cell.row
                worksheet.update_cell(row, 8, stake)  # Coloana H = last_stake
                worksheet.update_cell(row, 12, datetime.utcnow().isoformat())  # updated_at
                logger.info(f"Ultima miză actualizată pentru {team_name}: {stake} RON")
                return True
            return False
        except Exception as e:
            logger.error(f"Eroare la actualizarea ultimei mize pentru {team_name}: {e}")
            return False

    def update_match_status(self, team_name: str, event_name: str, status: str, stake: float = None, profit: float = None, bet_id: str = None) -> bool:
        """Actualizează statusul unui meci în sheet-ul echipei."""
        if not self._connected:
            return False

        try:
            worksheet = self._spreadsheet.worksheet(team_name)
            cell = worksheet.find(event_name)

            if cell:
                row = cell.row
                if stake is not None:
                    worksheet.update_cell(row, 5, stake)  # Miză
                worksheet.update_cell(row, 6, status)  # Status
                if profit is not None:
                    worksheet.update_cell(row, 7, profit)  # Profit
                if bet_id:
                    worksheet.update_cell(row, 8, bet_id)  # Bet ID
                return True
            return False

        except Exception as e:
            logger.error(f"Eroare la actualizarea meciului {event_name}: {e}")
            return False

    def get_scheduled_matches(self, team_name: str) -> List[Dict[str, Any]]:
        """Obține meciurile programate pentru o echipă."""
        if not self._connected:
            return []

        try:
            worksheet = self._spreadsheet.worksheet(team_name)
            records = worksheet.get_all_records()

            matches = []
            for record in records:
                if record.get("Status") == "PROGRAMAT":
                    matches.append(record)

            return matches

        except Exception as e:
            logger.error(f"Eroare la citirea meciurilor pentru {team_name}: {e}")
            return []

    def delete_team(self, team_id: str) -> bool:
        """Șterge o echipă din Google Sheets (Index + sheet-ul echipei)."""
        if not self._connected:
            self.connect()

        if not self._connected:
            return False

        try:
            worksheet = self._spreadsheet.worksheet("Index")
            cell = worksheet.find(team_id)

            if cell:
                row_values = worksheet.row_values(cell.row)
                team_name = row_values[1] if len(row_values) > 1 else None

                worksheet.delete_rows(cell.row)
                logger.info(f"Echipă ștearsă din Index: {team_id}")

                if team_name:
                    try:
                        team_sheet = self._spreadsheet.worksheet(team_name)
                        self._spreadsheet.del_worksheet(team_sheet)
                        logger.info(f"Sheet șters: {team_name}")
                    except Exception as e:
                        logger.warning(f"Nu s-a putut șterge sheet-ul {team_name}: {e}")

                return True
            return False

        except Exception as e:
            logger.error(f"Eroare la ștergerea echipei: {e}")
            return False

    def save_bet(self, bet: Dict[str, Any]) -> bool:
        """Salvează un pariu în Google Sheets."""
        if not self._connected:
            return False

        try:
            headers = ["id", "team_id", "team_name", "event_name", "pronostic",
                      "odds", "stake", "potential_profit", "result", "status",
                      "placed_at", "settled_at", "created_at"]
            worksheet = self._get_or_create_worksheet("Istoric", headers)

            row_data = [
                bet["id"],
                bet["team_id"],
                bet["team_name"],
                bet["event_name"],
                bet["pronostic"],
                bet["odds"],
                bet["stake"],
                bet["potential_profit"],
                bet.get("result", ""),
                bet["status"],
                bet.get("placed_at", ""),
                bet.get("settled_at", ""),
                bet.get("created_at", datetime.utcnow().isoformat())
            ]

            cell = worksheet.find(bet["id"]) if worksheet.row_count > 1 else None

            if cell:
                row_num = cell.row
                worksheet.update(f"A{row_num}:M{row_num}", [row_data])
            else:
                worksheet.append_row(row_data)

            return True

        except Exception as e:
            logger.error(f"Eroare la salvarea pariului: {e}")
            return False

    def load_bets(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Încarcă pariurile din Google Sheets."""
        if not self._connected:
            return []

        try:
            worksheet = self._spreadsheet.worksheet("Istoric")
            records = worksheet.get_all_records()

            bets = []
            for record in records[-limit:]:
                if record.get("id"):
                    bets.append(record)

            return bets

        except Exception as e:
            logger.error(f"Eroare la încărcarea pariurilor: {e}")
            return []

    def get_pending_bets(self, team_name: str = None) -> List[Dict[str, Any]]:
        """
        Obține pariurile cu status PENDING.

        Args:
            team_name: Dacă e specificat, returnează doar pentru acea echipă.
                      Dacă e None, returnează din toate echipele.

        Returns:
            Lista de pariuri pending cu team_name inclus
        """
        if not self._connected:
            return []

        pending_bets = []

        try:
            # Dacă avem team_name specific, căutăm doar în acel sheet
            if team_name:
                try:
                    worksheet = self._spreadsheet.worksheet(team_name)
                    records = worksheet.get_all_records()

                    for record in records:
                        if record.get("Status") == "PENDING":
                            record["team_name"] = team_name
                            pending_bets.append(record)
                except Exception as e:
                    logger.warning(f"Nu s-a putut citi sheet-ul pentru {team_name}: {e}")

                return pending_bets

            # Altfel, căutăm în toate echipele
            teams = self.load_teams()

            for team in teams:
                t_name = team.get("name", "")
                if not t_name:
                    continue

                try:
                    worksheet = self._spreadsheet.worksheet(t_name)
                    records = worksheet.get_all_records()

                    for record in records:
                        if record.get("Status") == "PENDING":
                            record["team_name"] = t_name
                            pending_bets.append(record)

                except Exception as e:
                    logger.warning(f"Nu s-a putut citi sheet-ul pentru {t_name}: {e}")
                    continue

            logger.info(f"Găsite {len(pending_bets)} pariuri PENDING")
            return pending_bets

        except Exception as e:
            logger.error(f"Eroare la citirea pariurilor pending: {e}")
            return []

    def update_bet_result(self, team_name: str, bet_id: str, status: str, profit: float = 0) -> bool:
        """
        Actualizează rezultatul unui pariu în sheet-ul echipei.

        Args:
            team_name: Numele echipei
            bet_id: ID-ul pariului Betfair
            status: WON sau LOST
            profit: Profitul (pozitiv pentru WIN, negativ pentru LOSE)

        Returns:
            True dacă actualizarea a reușit
        """
        if not self._connected:
            return False

        try:
            worksheet = self._spreadsheet.worksheet(team_name)

            # Find the row with this bet_id
            cell = worksheet.find(str(bet_id))

            if not cell:
                logger.warning(f"Nu s-a găsit pariul {bet_id} în sheet-ul {team_name}")
                return False

            row = cell.row

            # Update Status (column F) and Profit (column G)
            worksheet.update_cell(row, 6, status)  # Status
            worksheet.update_cell(row, 7, profit)  # Profit

            logger.info(f"Actualizat pariu {bet_id}: {status}, profit: {profit}")
            return True

        except Exception as e:
            logger.error(f"Eroare la actualizarea pariului {bet_id}: {e}")
            return False

    def update_team_progression_after_result(self, team_name: str, won: bool, stake: float) -> bool:
        """
        Actualizează progresia echipei în Index sheet după rezultatul unui pariu.
        """
        if not self._connected:
            return False

        try:
            worksheet = self._spreadsheet.worksheet("Index")
            cell = worksheet.find(team_name)

            if not cell:
                logger.warning(f"Echipa {team_name} nu a fost găsită în Index")
                return False

            row = cell.row
            row_values = worksheet.row_values(row)

            current_loss = float(row_values[6]) if len(row_values) > 6 and row_values[6] else 0
            current_step = int(row_values[8]) if len(row_values) > 8 and row_values[8] else 0

            if won:
                new_cumulative_loss = 0
                new_step = 0
                logger.info(f"WIN pentru {team_name} - Reset progresie")
            else:
                new_cumulative_loss = current_loss + stake
                new_step = current_step + 1
                logger.info(f"LOSE pentru {team_name} - Progresie: loss={new_cumulative_loss}, step={new_step}")

            worksheet.update_cell(row, 7, new_cumulative_loss)
            worksheet.update_cell(row, 8, stake)
            worksheet.update_cell(row, 9, new_step)
            worksheet.update_cell(row, 12, datetime.utcnow().isoformat())

            return True

        except Exception as e:
            logger.error(f"Eroare la actualizarea progresiei pentru {team_name}: {e}")
            return False


google_sheets_client = GoogleSheetsClient()

# Auto-configure from environment variables
def auto_configure_google_sheets():
    """Auto-configure Google Sheets from environment variables."""
    from app.config import get_settings

    settings = get_settings()
    spreadsheet_id = settings.google_sheets_spreadsheet_id
    credentials_path = settings.google_sheets_credentials_path

    if spreadsheet_id:
        google_sheets_client.configure(
            spreadsheet_id=spreadsheet_id,
            credentials_path=credentials_path
        )
        logger.info(f"Google Sheets auto-configured with spreadsheet: {spreadsheet_id}")
    else:
        logger.warning("GOOGLE_SHEETS_SPREADSHEET_ID not found in settings")

auto_configure_google_sheets()
