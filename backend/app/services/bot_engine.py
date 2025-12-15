import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import uuid4

from app.models.schemas import (
    Team, TeamStatus, Bet, BetStatus, BetCreate,
    Match, BotState, BotStatus, DashboardStats
)
from app.services.staking import staking_service
from app.config import get_settings

logger = logging.getLogger(__name__)


class BotEngine:
    """
    Motor principal al botului de pariuri.
    Coordonează toate operațiunile: scanare meciuri, calcul mize, plasare pariuri.
    """

    def __init__(self):
        self.settings = get_settings()
        self.state = BotState()
        self._teams: Dict[str, Team] = {}
        self._bets: Dict[str, Bet] = {}
        self._betfair_client = None
        self._sheets_client = None

    def set_betfair_client(self, client) -> None:
        """Setează clientul Betfair API."""
        self._betfair_client = client

    def set_sheets_client(self, client) -> None:
        """Setează clientul Google Sheets."""
        self._sheets_client = client

    def get_state(self) -> BotState:
        """Returnează starea curentă a botului."""
        return self.state

    def start(self) -> bool:
        """Pornește botul."""
        if self.state.status == BotStatus.RUNNING:
            logger.warning("Botul rulează deja")
            return False

        self.state.status = BotStatus.RUNNING
        self.state.last_error = None
        logger.info("Bot pornit")
        return True

    def stop(self) -> bool:
        """Oprește botul."""
        if self.state.status == BotStatus.STOPPED:
            logger.warning("Botul este deja oprit")
            return False

        self.state.status = BotStatus.STOPPED
        logger.info("Bot oprit")
        return True

    def get_all_teams(self) -> List[Team]:
        """Returnează toate echipele din Google Sheets (Index - fără statistici pentru a evita rate limit)."""
        from app.services.google_sheets import google_sheets_client

        if not google_sheets_client.is_connected():
            google_sheets_client.connect()

        if not google_sheets_client.is_connected():
            logger.warning("Google Sheets nu este conectat")
            return list(self._teams.values())

        try:
            teams_data = google_sheets_client.load_teams()
            teams = []

            for team_data in teams_data:
                team_name = team_data.get("name", "")
                if not team_name:
                    continue

                team = Team(
                    id=team_data.get("id", str(uuid4())),
                    name=team_name,
                    betfair_id=team_data.get("betfair_id", ""),
                    sport=team_data.get("sport", "football"),
                    league=team_data.get("league", ""),
                    country=team_data.get("country", ""),
                    cumulative_loss=float(team_data.get("cumulative_loss", 0)),
                    progression_step=int(team_data.get("progression_step", 0)),
                    last_stake=float(team_data.get("last_stake", 0)),
                    status=TeamStatus.ACTIVE if team_data.get("status") == "active" else TeamStatus.PAUSED,
                    total_matches=0,
                    matches_won=0,
                    matches_lost=0,
                    total_profit=0.0
                )
                teams.append(team)

            return teams
        except Exception as e:
            logger.error(f"Eroare la citirea echipelor din Google Sheets: {e}")
            return list(self._teams.values())

    def get_active_teams(self) -> List[Team]:
        """Returnează doar echipele active."""
        return [t for t in self._teams.values() if t.status == TeamStatus.ACTIVE]

    def get_team(self, team_id: str) -> Optional[Team]:
        """Returnează o echipă după ID."""
        return self._teams.get(team_id)

    def add_team(self, team: Team) -> Team:
        """Adaugă o echipă nouă."""
        if not team.id:
            team.id = str(uuid4())
        self._teams[team.id] = team
        logger.info(f"Echipă adăugată: {team.name}")
        return team

    def update_team(self, team_id: str, updates: Dict[str, Any]) -> Optional[Team]:
        """Actualizează o echipă."""
        team = self._teams.get(team_id)
        if not team:
            return None

        for key, value in updates.items():
            if hasattr(team, key) and value is not None:
                setattr(team, key, value)

        team.updated_at = datetime.utcnow()
        self._teams[team_id] = team
        logger.info(f"Echipă actualizată: {team.name}")
        return team

    def delete_team(self, team_id: str) -> bool:
        """Șterge o echipă din Google Sheets."""
        from app.services.google_sheets import google_sheets_client

        if team_id in self._teams:
            self._teams.pop(team_id)

        success = google_sheets_client.delete_team(team_id)
        if success:
            logger.info(f"Echipă ștearsă: {team_id}")
        return success

    def reset_team_progression(self, team_id: str) -> Optional[Team]:
        """Resetează progresia unei echipe."""
        team = self._teams.get(team_id)
        if not team:
            return None

        team.cumulative_loss = 0.0
        team.last_stake = self.settings.bot_initial_stake
        team.progression_step = 0
        team.updated_at = datetime.utcnow()

        logger.info(f"Progresie resetată pentru: {team.name}")
        return team

    def get_all_bets(self) -> List[Bet]:
        """Returnează toate pariurile."""
        return list(self._bets.values())

    def get_pending_bets(self) -> List[Bet]:
        """Returnează pariurile în așteptare."""
        return [b for b in self._bets.values() if b.status in [BetStatus.PENDING, BetStatus.PLACED, BetStatus.MATCHED]]

    def get_bet(self, bet_id: str) -> Optional[Bet]:
        """Returnează un pariu după ID."""
        return self._bets.get(bet_id)

    def get_bets_by_team(self, team_id: str) -> List[Bet]:
        """Returnează pariurile pentru o echipă."""
        return [b for b in self._bets.values() if b.team_id == team_id]

    def determine_pronostic(self, team_name: str, home_team: str, away_team: str) -> Optional[int]:
        """
        Determină pronosticul (1 sau 2) în funcție de unde joacă echipa.

        Args:
            team_name: Numele echipei noastre
            home_team: Echipa gazdă
            away_team: Echipa oaspete

        Returns:
            1 dacă echipa joacă acasă, 2 dacă în deplasare, None dacă nu e găsită
        """
        team_name_lower = team_name.lower()
        home_lower = home_team.lower()
        away_lower = away_team.lower()

        if team_name_lower in home_lower or home_lower in team_name_lower:
            return 1
        elif team_name_lower in away_lower or away_lower in team_name_lower:
            return 2

        return None

    def prepare_bet_for_team(self, team: Team, match: Match) -> Optional[BetCreate]:
        """
        Pregătește un pariu pentru o echipă bazat pe meciul găsit.

        Args:
            team: Echipa pentru care pariem
            match: Meciul găsit pe Betfair

        Returns:
            BetCreate sau None dacă nu se poate paria
        """
        pronostic = self.determine_pronostic(team.name, match.home_team, match.away_team)
        if pronostic is None:
            logger.warning(f"Nu s-a putut determina pronosticul pentru {team.name} în {match.event_name}")
            return None

        if pronostic == 1:
            odds = match.home_odds
            selection_id = match.home_selection_id
        else:
            odds = match.away_odds
            selection_id = match.away_selection_id

        if odds is None or odds <= 1.0:
            logger.warning(f"Cotă invalidă pentru {team.name}: {odds}")
            return None

        stake, stop_loss_reached = staking_service.calculate_stake(
            team.cumulative_loss,
            odds,
            team.progression_step
        )

        if stop_loss_reached:
            logger.warning(f"Stop loss atins pentru {team.name} la pasul {team.progression_step}")
            return None

        return BetCreate(
            team_id=team.id,
            event_name=match.event_name,
            event_id=match.event_id,
            market_id=match.market_id,
            selection_id=selection_id,
            pronostic=pronostic,
            odds=odds,
            stake=stake
        )

    def create_bet(self, bet_create: BetCreate, team: Team) -> Bet:
        """Creează un obiect Bet din BetCreate."""
        potential_profit = staking_service.calculate_potential_profit(
            bet_create.stake, bet_create.odds
        )

        bet = Bet(
            id=str(uuid4()),
            team_id=bet_create.team_id,
            team_name=team.name,
            event_name=bet_create.event_name,
            event_id=bet_create.event_id,
            market_id=bet_create.market_id,
            selection_id=bet_create.selection_id,
            pronostic=bet_create.pronostic,
            odds=bet_create.odds,
            stake=bet_create.stake,
            potential_profit=potential_profit,
            status=BetStatus.PENDING
        )

        self._bets[bet.id] = bet
        return bet

    def update_bet_status(
        self,
        bet_id: str,
        status: BetStatus,
        betfair_bet_id: Optional[str] = None,
        result: Optional[float] = None
    ) -> Optional[Bet]:
        """Actualizează statusul unui pariu."""
        bet = self._bets.get(bet_id)
        if not bet:
            return None

        bet.status = status

        if betfair_bet_id:
            bet.bet_id = betfair_bet_id

        if status == BetStatus.PLACED:
            bet.placed_at = datetime.utcnow()

        if result is not None:
            bet.result = result
            bet.settled_at = datetime.utcnow()

        self._bets[bet_id] = bet
        return bet

    def process_bet_result(self, bet: Bet, won: bool) -> None:
        """
        Procesează rezultatul unui pariu și actualizează echipa.

        Args:
            bet: Pariul finalizat
            won: True dacă a fost câștigat
        """
        team = self._teams.get(bet.team_id)
        if not team:
            logger.error(f"Echipa {bet.team_id} nu a fost găsită pentru pariul {bet.id}")
            return

        if won:
            profit, new_cumulative_loss, new_progression_step = staking_service.process_win(
                bet.stake, bet.odds
            )
            bet.status = BetStatus.WON
            bet.result = profit
        else:
            loss, new_cumulative_loss, new_progression_step = staking_service.process_loss(
                bet.stake, team.cumulative_loss, team.progression_step
            )
            bet.status = BetStatus.LOST
            bet.result = loss

        bet.settled_at = datetime.utcnow()
        self._bets[bet.id] = bet

        team.cumulative_loss = new_cumulative_loss
        team.progression_step = new_progression_step
        team.last_stake = bet.stake
        team.updated_at = datetime.utcnow()
        self._teams[team.id] = team

        logger.info(
            f"Pariu procesat: {team.name} - {'WIN' if won else 'LOSE'} - "
            f"Rezultat: {bet.result}, Pierdere cumulată: {team.cumulative_loss}"
        )

    def get_dashboard_stats(self) -> DashboardStats:
        """Calculează statisticile pentru dashboard din Google Sheets (cu cache 60s)."""
        from app.services.google_sheets import google_sheets_client

        cache_key = "dashboard_stats"
        cached = google_sheets_client._get_cached(cache_key)
        if cached is not None:
            return cached

        total_teams = 0
        active_teams = 0
        won_bets = 0
        lost_bets = 0
        pending_bets = 0
        total_profit = 0.0
        total_staked = 0.0

        try:
            if not google_sheets_client.is_connected():
                google_sheets_client.connect()

            if not google_sheets_client.is_connected():
                logger.warning("Google Sheets nu este conectat pentru stats")
                return DashboardStats(
                    total_teams=0, active_teams=0, total_bets=0,
                    won_bets=0, lost_bets=0, pending_bets=0,
                    total_profit=0.0, win_rate=0.0, total_staked=0.0
                )

            teams_data = google_sheets_client.load_teams()
            total_teams = len(teams_data)
            active_teams = len([t for t in teams_data if t.get("status") == "active"])

            for team_data in teams_data:
                team_name = team_data.get("name", "")
                if not team_name:
                    continue

                try:
                    sheet = google_sheets_client._spreadsheet.worksheet(team_name)
                    all_records = sheet.get_all_records()

                    for match in all_records:
                        status = str(match.get("Status", "")).strip().upper()
                        stake = 0.0
                        profit = 0.0

                        try:
                            stake = float(match.get("Miză", 0) or 0)
                        except:
                            pass

                        try:
                            profit = float(match.get("Profit", 0) or 0)
                        except:
                            pass

                        if status == "WON":
                            won_bets += 1
                            total_profit += profit
                            total_staked += stake
                        elif status == "LOST":
                            lost_bets += 1
                            total_profit += profit
                            total_staked += stake
                        elif status == "PENDING":
                            pending_bets += 1
                            total_staked += stake

                except Exception as e:
                    logger.warning(f"Eroare citire stats pentru {team_name}: {e}")

        except Exception as e:
            logger.error(f"Eroare la calcularea statisticilor din Sheets: {e}")

        total_bets = won_bets + lost_bets + pending_bets
        settled_bets = won_bets + lost_bets
        win_rate = (won_bets / settled_bets * 100) if settled_bets > 0 else 0.0

        result = DashboardStats(
            total_teams=total_teams,
            active_teams=active_teams,
            total_bets=total_bets,
            won_bets=won_bets,
            lost_bets=lost_bets,
            pending_bets=pending_bets,
            total_profit=round(total_profit, 2),
            win_rate=round(win_rate, 2),
            total_staked=round(total_staked, 2)
        )

        google_sheets_client._set_cached(cache_key, result)
        return result

    async def run_cycle(self) -> Dict[str, Any]:
        """
        Execută un ciclu complet al botului:
        1. Încarcă echipele din Google Sheets
        2. Verifică meciurile de azi
        3. Calculează mizele
        4. Plasează pariurile
        5. Actualizează Google Sheets
        """
        # Start bot if not running
        if self.state.status != BotStatus.RUNNING:
            self.state.status = BotStatus.RUNNING
            logger.info("Bot pornit automat pentru execuție programată")

        self.state.last_run = datetime.utcnow()
        self.state.bets_placed_today = 0
        self.state.total_stake_today = 0.0

        results = {
            "success": True,
            "timestamp": datetime.utcnow().isoformat(),
            "teams_checked": 0,
            "matches_found": 0,
            "bets_placed": 0,
            "total_stake": 0.0,
            "errors": []
        }

        try:
            from app.services.google_sheets import google_sheets_client
            from app.services.betfair_client import betfair_client
            from datetime import date

            # Connect to Google Sheets
            if not google_sheets_client.is_connected():
                google_sheets_client.connect()

            if not google_sheets_client.is_connected():
                results["success"] = False
                results["message"] = "Nu s-a putut conecta la Google Sheets"
                return results

            # Load teams from Google Sheets
            teams_data = google_sheets_client.load_teams()
            results["teams_checked"] = len(teams_data)

            if not teams_data:
                results["message"] = "Nu există echipe în Google Sheets"
                return results

            # Connect to Betfair
            if not betfair_client.is_connected():
                await betfair_client.connect()

            if not betfair_client.is_connected():
                results["success"] = False
                results["message"] = "Nu s-a putut conecta la Betfair"
                return results

            logger.info("Verificare meciuri PROGRAMAT pentru toate echipele active")

            for team_data in teams_data:
                team_name = team_data.get("name", "")
                if team_data.get("status") != "active":
                    continue

                try:
                    # IMPORTANT: Verifică dacă echipa are deja un pariu PENDING
                    # Dacă da, NU plasa alt pariu până nu se rezolvă cel curent!
                    pending_bets = google_sheets_client.get_pending_bets(team_name)
                    if pending_bets:
                        logger.info(f"Skip {team_name} - are deja {len(pending_bets)} pariu(ri) PENDING")
                        continue

                    # Get scheduled matches from team's sheet
                    scheduled_matches = google_sheets_client.get_scheduled_matches(team_name)

                    if not scheduled_matches:
                        logger.info(f"Nu există meciuri programate pentru {team_name}")
                        continue

                    # Sort matches by date and take only the first one (closest date)
                    sorted_matches = sorted(scheduled_matches, key=lambda x: x.get("Data", ""))
                    match = sorted_matches[0] if sorted_matches else None

                    if not match:
                        continue

                    event_name = match.get("Meci", "")
                    match_date_str = match.get("Data", "")  # Format: 2025-11-29T21:45
                    odds_str = match.get("Cotă", "")

                    if not odds_str:
                        logger.warning(f"Lipsește cota pentru {event_name}")
                        continue

                    try:
                        odds = float(odds_str)
                    except:
                        logger.warning(f"Cotă invalidă pentru {event_name}: {odds_str}")
                        continue

                    results["matches_found"] += 1

                    # Calculate stake - folosim miza inițială per echipă
                    cumulative_loss = float(team_data.get("cumulative_loss", 0))
                    progression_step = int(team_data.get("progression_step", 0))
                    team_initial_stake = float(team_data.get("initial_stake", 5))

                    stake, stop_loss = staking_service.calculate_stake(
                        cumulative_loss, odds, progression_step, team_initial_stake
                    )

                    logger.info(f"{team_name}: initial_stake={team_initial_stake}, loss={cumulative_loss}, step={progression_step} => miză={stake}")

                    if stop_loss:
                        logger.warning(f"Stop loss atins pentru {team_name}")
                        continue

                    logger.info(f"Plasare pariu: {team_name} - {event_name} - Miză: {stake} @ {odds}")

                    # Find market on Betfair and place bet
                    # Extract main team name (remove FC, United, etc for better matching)
                    search_terms = [team_name]
                    # Try without common suffixes
                    for suffix in [" FC", " United FC", " United"]:
                        if team_name.endswith(suffix):
                            search_terms.append(team_name[:-len(suffix)])

                    events = None
                    for search_term in search_terms:
                        events = await betfair_client.list_events(
                            event_type_id="1",
                            text_query=search_term
                        )
                        if events:
                            logger.info(f"Găsit evenimente cu search term: {search_term}")
                            break

                    if not events:
                        logger.warning(f"Nu s-a găsit evenimentul pe Betfair: {event_name}")
                        continue

                    # Find matching event BY DATE
                    # Extragem doar data (YYYY-MM-DD) din match_date_str pentru comparare
                    match_date_only = match_date_str[:10] if match_date_str else ""  # "2025-11-29"

                    event_id = None
                    matched_event_name = None
                    for ev in events:
                        ev_data = ev.get("event", {})
                        ev_name = ev_data.get("name", "")
                        ev_open_date = ev_data.get("openDate", "")  # "2025-12-04T20:00:00.000Z"
                        ev_date_only = ev_open_date[:10] if ev_open_date else ""  # "2025-12-04"

                        # Verificăm dacă numele se potrivește ȘI data e aceeași
                        name_matches = False
                        for search_term in search_terms:
                            if search_term.lower() in ev_name.lower():
                                name_matches = True
                                break

                        if name_matches and ev_date_only == match_date_only:
                            event_id = ev_data.get("id")
                            matched_event_name = ev_name
                            logger.info(f"Match găsit cu data corectă: {ev_name} (event_id: {event_id}, data: {ev_date_only})")
                            break
                        elif name_matches:
                            logger.info(f"Eveniment găsit dar data nu se potrivește: {ev_name} (Betfair: {ev_date_only}, Sheets: {match_date_only})")

                    if not event_id:
                        logger.warning(f"Nu s-a găsit event_id pentru {team_name} cu data {match_date_only}")
                        continue

                    # Get market
                    markets = await betfair_client.list_market_catalogue(
                        event_ids=[event_id],
                        market_type_codes=["MATCH_ODDS"]
                    )

                    if not markets:
                        logger.warning(f"Nu s-a găsit piața pentru {event_name}")
                        continue

                    market = markets[0]
                    market_id = market.get("marketId", "")

                    # Get selection ID - găsim runner-ul care conține numele echipei noastre
                    runners = market.get("runners", [])
                    if not runners:
                        logger.warning(f"Nu s-au găsit runners pentru {event_name}")
                        continue

                    # Căutăm runner-ul echipei noastre (nu primul runner!)
                    selection_id = None
                    selected_runner_name = None
                    for runner in runners:
                        runner_name = runner.get("runnerName", "")
                        # Verificăm dacă numele echipei se potrivește EXACT cu runner-ul
                        for search_term in search_terms:
                            if search_term.lower() == runner_name.lower():
                                selection_id = str(runner.get("selectionId", ""))
                                selected_runner_name = runner_name
                                break
                        if selection_id:
                            break

                    if not selection_id:
                        logger.warning(f"Nu s-a găsit runner pentru echipa {team_name} în meciul {event_name}")
                        logger.warning(f"  Runners disponibili: {[r.get('runnerName') for r in runners]}")
                        continue

                    logger.info(f"Selectat runner: {selected_runner_name} (ID: {selection_id}) pentru {team_name}")

                    # Place bet
                    place_result = await betfair_client.place_bet(
                        market_id=market_id,
                        selection_id=selection_id,
                        stake=stake,
                        odds=odds
                    )

                    if place_result.success:
                        results["bets_placed"] += 1
                        results["total_stake"] += stake
                        self.state.bets_placed_today += 1
                        self.state.total_stake_today += stake

                        # Update Google Sheets - match status
                        google_sheets_client.update_match_status(
                            team_name, event_name, "PENDING",
                            stake=stake, bet_id=place_result.bet_id
                        )

                        # Update last_stake în Index
                        google_sheets_client.update_last_stake(team_name, stake)

                        logger.info(
                            f"Pariu plasat: {team_name} - {event_name} - "
                            f"Miză: {stake} RON @ {odds} - Bet ID: {place_result.bet_id}"
                        )
                    else:
                        results["errors"].append(
                            f"Eroare plasare pariu {team_name}: {place_result.error_message}"
                        )
                        google_sheets_client.update_match_status(
                            team_name, event_name, "ERROR"
                        )

                except Exception as e:
                    error_msg = f"Eroare procesare {team_name}: {str(e)}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)

            results["message"] = f"Ciclu complet: {results['bets_placed']} pariuri plasate"

        except Exception as e:
            self.state.status = BotStatus.ERROR
            self.state.last_error = str(e)
            results["success"] = False
            results["message"] = f"Eroare critică: {str(e)}"
            logger.error(f"Eroare critică în ciclul botului: {e}")

        return results

    async def check_bet_results(self) -> Dict[str, Any]:
        """
        Verifică rezultatele pariurilor PENDING.
        Funcție NOUĂ - NU modifică run_cycle().

        Flow:
        1. Citește pariurile PENDING din Google Sheets
        2. Verifică pe Betfair dacă sunt settled
        3. Actualizează status (WON/LOST) în Google Sheets
        4. Actualizează progresia echipei

        Returns:
            Dict cu rezultatele verificării
        """
        results = {
            "success": True,
            "timestamp": datetime.utcnow().isoformat(),
            "pending_checked": 0,
            "settled_found": 0,
            "won": 0,
            "lost": 0,
            "still_pending": 0,
            "errors": []
        }

        try:
            from app.services.google_sheets import google_sheets_client
            from app.services.betfair_client import betfair_client

            # Connect to Google Sheets
            if not google_sheets_client.is_connected():
                google_sheets_client.connect()

            if not google_sheets_client.is_connected():
                results["success"] = False
                results["message"] = "Nu s-a putut conecta la Google Sheets"
                return results

            # Get pending bets from Google Sheets
            pending_bets = google_sheets_client.get_pending_bets()
            results["pending_checked"] = len(pending_bets)

            if not pending_bets:
                results["message"] = "Nu există pariuri PENDING de verificat"
                return results

            logger.info(f"Verificare {len(pending_bets)} pariuri PENDING")

            # Connect to Betfair
            if not betfair_client.is_connected():
                await betfair_client.connect()

            if not betfair_client.is_connected():
                results["success"] = False
                results["message"] = "Nu s-a putut conecta la Betfair"
                return results

            # Get settled orders from Betfair (ultimele 3 zile pentru siguranță)
            settled_orders = await betfair_client.get_settled_orders(days=3)

            # Create a map of bet_id -> settled order
            settled_map = {}
            for order in settled_orders:
                bet_id = str(order.get("betId", ""))
                if bet_id:
                    settled_map[bet_id] = order

            logger.info(f"Găsite {len(settled_map)} ordine settled pe Betfair (ultimele 3 zile)")

            # Log detaliat pentru debugging
            if settled_orders:
                logger.info("=== SETTLED ORDERS DE PE BETFAIR ===")
                for order in settled_orders[:10]:  # Primele 10
                    logger.info(f"  Bet ID: {order.get('betId')}, Profit: {order.get('profit')}, SettledDate: {order.get('settledDate')}")

            # Log pariuri pending pentru debugging
            logger.info("=== PARIURI PENDING DIN GOOGLE SHEETS ===")
            for bet in pending_bets:
                logger.info(f"  Team: {bet.get('team_name')}, Bet ID: {bet.get('Bet ID')}, Meci: {bet.get('Meci')}")

            # Check each pending bet
            for bet in pending_bets:
                bet_id = str(bet.get("Bet ID", ""))
                team_name = bet.get("team_name", "")
                meci = bet.get("Meci", "")
                stake = float(bet.get("Miză", 0) or 0)

                if not bet_id or not team_name:
                    logger.warning(f"Skip pariu invalid: bet_id={bet_id}, team={team_name}")
                    continue

                if bet_id in settled_map:
                    # Bet is settled
                    settled_order = settled_map[bet_id]
                    profit = float(settled_order.get("profit", 0))

                    if profit > 0:
                        # WON
                        status = "WON"
                        results["won"] += 1
                        won = True
                        logger.info(f"Pariu CÂȘTIGAT: {team_name} - Bet ID: {bet_id} - Profit: {profit}")
                    else:
                        # LOST
                        status = "LOST"
                        results["lost"] += 1
                        won = False
                        logger.info(f"Pariu PIERDUT: {team_name} - Bet ID: {bet_id} - Loss: {profit}")

                    results["settled_found"] += 1

                    # Update Google Sheets
                    google_sheets_client.update_bet_result(team_name, bet_id, status, profit)
                    google_sheets_client.update_team_progression_after_result(team_name, won, stake)

                else:
                    # Still pending - log mai detaliat
                    results["still_pending"] += 1
                    logger.info(f"Pariu încă în așteptare: {team_name} - {meci} - Bet ID: {bet_id} (nu e în settled_map)")

                    # Verifică dacă pariul există măcar în current orders
                    current_orders = await betfair_client.get_current_orders()
                    found_in_current = any(str(o.get('betId')) == bet_id for o in current_orders)
                    if found_in_current:
                        logger.info(f"  → Pariul {bet_id} există în CURRENT ORDERS (meci în desfășurare sau neterminat)")
                    else:
                        logger.warning(f"  → Pariul {bet_id} NU există nici în current orders! Posibil problemă.")

            results["message"] = f"Verificare completă: {results['won']} WIN, {results['lost']} LOST, {results['still_pending']} în așteptare"

        except Exception as e:
            results["success"] = False
            results["message"] = f"Eroare la verificare: {str(e)}"
            logger.error(f"Eroare la verificarea rezultatelor: {e}")

        return results

    async def refresh_all_team_matches(self) -> Dict[str, Any]:
        """
        Actualizează meciurile pentru toate echipele active.
        Preia meciuri noi de pe Betfair și le adaugă în Google Sheets.
        NU resetează progresia!

        Returns:
            Dict cu rezultatele actualizării
        """
        results = {
            "success": True,
            "timestamp": datetime.utcnow().isoformat(),
            "teams_updated": 0,
            "matches_added": 0,
            "errors": []
        }

        try:
            from app.services.google_sheets import google_sheets_client
            from app.services.betfair_client import betfair_client
            import pytz

            # Connect to services
            if not google_sheets_client.is_connected():
                google_sheets_client.connect()

            if not google_sheets_client.is_connected():
                results["success"] = False
                results["message"] = "Nu s-a putut conecta la Google Sheets"
                return results

            if not betfair_client.is_connected():
                await betfair_client.connect()

            if not betfair_client.is_connected():
                results["success"] = False
                results["message"] = "Nu s-a putut conecta la Betfair"
                return results

            # Get all active teams from Index
            teams_data = google_sheets_client.load_teams()
            active_teams = [t for t in teams_data if t.get("status") == "active"]

            logger.info(f"Actualizare meciuri pentru {len(active_teams)} echipe active")

            # Skip keywords pentru echipe rezerve/tineret
            skip_keywords = ["(Res)", "U19", "U21", "U23", "Women", "Feminin", "II", "B)", "(W)"]

            for team_data in active_teams:
                team_name = team_data.get("name", "")

                try:
                    # Get events from Betfair
                    events = await betfair_client.list_events(
                        event_type_id="1",
                        text_query=team_name
                    )

                    if not events:
                        logger.info(f"Nu s-au găsit evenimente pentru {team_name}")
                        continue

                    matches_to_add = []

                    for event in events[:20]:
                        event_data = event.get("event", {})
                        event_id = event_data.get("id", "")
                        event_name = event_data.get("name", "")

                        # Skip reserve/youth teams
                        if any(kw in event_name for kw in skip_keywords):
                            continue

                        # Get market info
                        if event_id:
                            try:
                                markets = await betfair_client.list_market_catalogue(
                                    event_ids=[event_id],
                                    market_type_codes=["MATCH_ODDS"]
                                )

                                if markets:
                                    market = markets[0]
                                    market_id = market.get("marketId", "")
                                    market_start_time_utc = market.get("marketStartTime", "")

                                    # Convert UTC to Europe/Bucharest
                                    market_start_time = ""
                                    if market_start_time_utc:
                                        try:
                                            utc_time = datetime.fromisoformat(market_start_time_utc.replace("Z", "+00:00"))
                                            bucharest_tz = pytz.timezone("Europe/Bucharest")
                                            local_time = utc_time.astimezone(bucharest_tz)
                                            market_start_time = local_time.strftime("%Y-%m-%dT%H:%M")
                                        except:
                                            market_start_time = market_start_time_utc

                                    # Get odds pentru echipa noastră (nu gazda!)
                                    odds = ""
                                    if market_id:
                                        prices = await betfair_client.list_market_book([market_id])
                                        if prices and prices[0].get("runners"):
                                            price_runners = prices[0].get("runners", [])
                                            market_runners = market.get("runners", [])

                                            # Găsim runner-ul echipei noastre (verificare EXACTĂ)
                                            team_selection_id = None
                                            for mr in market_runners:
                                                runner_name = mr.get("runnerName", "")
                                                if team_name.lower() == runner_name.lower():
                                                    team_selection_id = mr.get("selectionId")
                                                    break

                                            # Luăm cota pentru echipa noastră
                                            if team_selection_id:
                                                for pr in price_runners:
                                                    if pr.get("selectionId") == team_selection_id:
                                                        back_prices = pr.get("ex", {}).get("availableToBack", [])
                                                        if back_prices:
                                                            odds = back_prices[0].get("price", "")
                                                        break
                                            else:
                                                # Fallback
                                                if price_runners:
                                                    back_prices = price_runners[0].get("ex", {}).get("availableToBack", [])
                                                    if back_prices:
                                                        odds = back_prices[0].get("price", "")

                                    matches_to_add.append({
                                        "start_time": market_start_time,
                                        "event_name": event_name,
                                        "competition": event.get("competitionName", ""),
                                        "odds": str(odds) if odds else ""
                                    })
                            except Exception as e:
                                logger.warning(f"Eroare la preluarea datelor pentru {event_name}: {e}")

                    if matches_to_add:
                        # Sort by date
                        matches_sorted = sorted(matches_to_add, key=lambda x: x.get("start_time", ""))

                        # Save to Google Sheets (funcția skipă meciurile existente)
                        saved = google_sheets_client.save_matches_for_team(team_name, matches_sorted)

                        if saved:
                            results["teams_updated"] += 1
                            results["matches_added"] += len(matches_sorted)
                            logger.info(f"Actualizat {team_name}: {len(matches_sorted)} meciuri verificate")

                except Exception as e:
                    error_msg = f"Eroare la actualizarea {team_name}: {str(e)}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)

            results["message"] = f"Actualizare completă: {results['teams_updated']} echipe, {results['matches_added']} meciuri verificate"

        except Exception as e:
            results["success"] = False
            results["message"] = f"Eroare la actualizare: {str(e)}"
            logger.error(f"Eroare la actualizarea meciurilor: {e}")

        return results


bot_engine = BotEngine()
