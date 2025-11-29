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
        """Returnează toate echipele din Google Sheets (Index + statistici din sheet-uri)."""
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

                total_matches = 0
                matches_won = 0
                matches_lost = 0
                total_profit = 0.0

                try:
                    sheet = google_sheets_client._spreadsheet.worksheet(team_name)
                    all_records = sheet.get_all_records()

                    for match in all_records:
                        status = str(match.get("Status", "")).strip().upper()

                        if status in ["WON", "LOST"]:
                            total_matches += 1
                            if status == "WON":
                                matches_won += 1
                            elif status == "LOST":
                                matches_lost += 1

                            try:
                                profit = float(match.get("Profit", 0))
                                total_profit += profit
                            except:
                                pass

                except Exception as e:
                    logger.warning(f"Eroare calculare statistici pentru {team_name}: {e}")

                team = Team(
                    id=team_data.get("id", str(uuid4())),
                    name=team_name,
                    betfair_id=team_data.get("betfair_id", ""),
                    sport=team_data.get("sport", "football"),
                    league=team_data.get("league", ""),
                    country=team_data.get("country", ""),
                    cumulative_loss=float(team_data.get("cumulative_loss", 0)),
                    progression_step=int(team_data.get("progression_step", 0)),
                    last_stake=float(team_data.get("last_stake", 100)),
                    status=TeamStatus.ACTIVE if team_data.get("status") == "active" else TeamStatus.PAUSED,
                    total_matches=total_matches,
                    matches_won=matches_won,
                    matches_lost=matches_lost,
                    total_profit=total_profit
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
        """Calculează statisticile pentru dashboard."""
        teams = list(self._teams.values())
        bets = list(self._bets.values())

        won_bets = [b for b in bets if b.status == BetStatus.WON]
        lost_bets = [b for b in bets if b.status == BetStatus.LOST]
        pending_bets = [b for b in bets if b.status in [BetStatus.PENDING, BetStatus.PLACED, BetStatus.MATCHED]]

        total_profit = sum(b.result or 0 for b in bets if b.result is not None)
        total_staked = sum(b.stake for b in bets if b.status != BetStatus.PENDING)

        settled_bets = len(won_bets) + len(lost_bets)
        win_rate = (len(won_bets) / settled_bets * 100) if settled_bets > 0 else 0.0

        return DashboardStats(
            total_teams=len(teams),
            active_teams=len([t for t in teams if t.status == TeamStatus.ACTIVE]),
            total_bets=len(bets),
            won_bets=len(won_bets),
            lost_bets=len(lost_bets),
            pending_bets=len(pending_bets),
            total_profit=round(total_profit, 2),
            win_rate=round(win_rate, 2),
            total_staked=round(total_staked, 2)
        )

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

            today = date.today().isoformat()
            logger.info(f"Verificare meciuri pentru data: {today}")

            for team_data in teams_data:
                team_name = team_data.get("name", "")
                if team_data.get("status") != "active":
                    continue

                try:
                    # Get scheduled matches from team's sheet
                    scheduled_matches = google_sheets_client.get_scheduled_matches(team_name)

                    if not scheduled_matches:
                        logger.info(f"Nu există meciuri programate pentru {team_name}")
                        continue

                    for match in scheduled_matches:
                        match_date = match.get("Data", "")

                        # Check if match is today
                        if not match_date or today not in match_date:
                            continue

                        event_name = match.get("Meci", "")
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

                        # Calculate stake
                        cumulative_loss = float(team_data.get("cumulative_loss", 0))
                        progression_step = int(team_data.get("progression_step", 0))

                        stake, stop_loss = staking_service.calculate_stake(
                            cumulative_loss, odds, progression_step
                        )

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

                        # Find matching event
                        event_id = None
                        for ev in events:
                            ev_name = ev.get("event", {}).get("name", "")
                            # Check if any search term matches
                            for search_term in search_terms:
                                if search_term.lower() in ev_name.lower():
                                    event_id = ev.get("event", {}).get("id")
                                    logger.info(f"Match găsit: {ev_name} (event_id: {event_id})")
                                    break
                            if event_id:
                                break

                        if not event_id:
                            logger.warning(f"Nu s-a găsit event_id pentru {team_name}")
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

                        # Get selection ID (first runner = home team)
                        runners = market.get("runners", [])
                        if not runners:
                            logger.warning(f"Nu s-au găsit runners pentru {event_name}")
                            continue

                        selection_id = str(runners[0].get("selectionId", ""))

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

                            # Update Google Sheets
                            google_sheets_client.update_match_status(
                                team_name, event_name, "PENDING",
                                stake=stake, bet_id=place_result.bet_id
                            )

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

            # Get settled orders from Betfair
            settled_orders = await betfair_client.get_settled_orders(days=1)

            # Create a map of bet_id -> settled order
            settled_map = {}
            for order in settled_orders:
                bet_id = str(order.get("betId", ""))
                if bet_id:
                    settled_map[bet_id] = order

            logger.info(f"Găsite {len(settled_map)} ordine settled pe Betfair")

            # Check each pending bet
            for bet in pending_bets:
                bet_id = str(bet.get("Bet ID", ""))
                team_name = bet.get("team_name", "")
                stake = float(bet.get("Miză", 0))

                if not bet_id or not team_name:
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
                    # Still pending
                    results["still_pending"] += 1
                    logger.info(f"Pariu încă în așteptare: {team_name} - Bet ID: {bet_id}")

            results["message"] = f"Verificare completă: {results['won']} WIN, {results['lost']} LOST, {results['still_pending']} în așteptare"

        except Exception as e:
            results["success"] = False
            results["message"] = f"Eroare la verificare: {str(e)}"
            logger.error(f"Eroare la verificarea rezultatelor: {e}")

        return results


bot_engine = BotEngine()
