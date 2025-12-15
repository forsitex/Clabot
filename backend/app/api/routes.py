from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Optional
from uuid import uuid4
from datetime import datetime
from pydantic import BaseModel

from app.models.schemas import (
    Team, TeamCreate, TeamUpdate, TeamStatus,
    Bet, BetStatus,
    BotState, BotStatus,
    DashboardStats, ApiResponse, Sport
)
from app.models.settings import AppSettings, SettingsUpdate
from app.services.bot_engine import bot_engine
from app.services.staking import staking_service
from app.services.settings_manager import settings_manager
from app.services.google_sheets import google_sheets_client
from app.services.betfair_client import betfair_client
from app.services.auth import authenticate, get_current_user

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    success: bool
    token: Optional[str] = None
    message: str


@router.post("/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Autentificare utilizator."""
    token = authenticate(request.username, request.password)
    if token:
        return LoginResponse(success=True, token=token, message="Autentificare reușită")
    return LoginResponse(success=False, message="Credențiale invalide")


@router.get("/auth/verify")
async def verify_auth(username: str = Depends(get_current_user)):
    """Verifică dacă token-ul este valid."""
    return {"valid": True, "username": username}


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats():
    """Returnează statisticile pentru dashboard."""
    return bot_engine.get_dashboard_stats()


@router.get("/stats/history")
async def get_stats_history(days: int = 30):
    """
    Returnează istoricul statisticilor pentru grafice.
    Doar citește date - nu modifică nimic.
    """
    from app.services.google_sheets import google_sheets_client
    from collections import defaultdict

    cache_key = f"stats_history_{days}"
    cached = google_sheets_client._get_cached(cache_key)
    if cached is not None:
        return cached

    daily_data = defaultdict(lambda: {"profit": 0.0, "won": 0, "lost": 0, "pending": 0, "staked": 0.0})
    team_profits = []

    try:
        if not google_sheets_client.is_connected():
            google_sheets_client.connect()

        if not google_sheets_client.is_connected():
            return {"daily": [], "team_profits": []}

        teams_data = google_sheets_client.load_teams()

        for team_data in teams_data:
            team_name = team_data.get("name", "")
            if not team_name:
                continue

            team_profit = 0.0
            team_won = 0
            team_lost = 0

            try:
                sheet = google_sheets_client._spreadsheet.worksheet(team_name)
                all_records = sheet.get_all_records()

                for match in all_records:
                    status = str(match.get("Status", "")).strip().upper()
                    date_str = str(match.get("Data", ""))[:10]  # YYYY-MM-DD

                    if not date_str or status not in ["WON", "LOST", "PENDING"]:
                        continue

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
                        daily_data[date_str]["won"] += 1
                        daily_data[date_str]["profit"] += profit
                        daily_data[date_str]["staked"] += stake
                        team_profit += profit
                        team_won += 1
                    elif status == "LOST":
                        daily_data[date_str]["lost"] += 1
                        daily_data[date_str]["profit"] += profit
                        daily_data[date_str]["staked"] += stake
                        team_profit += profit
                        team_lost += 1
                    elif status == "PENDING":
                        daily_data[date_str]["pending"] += 1
                        daily_data[date_str]["staked"] += stake

            except Exception:
                pass

            if team_won > 0 or team_lost > 0:
                team_profits.append({
                    "name": team_name,
                    "profit": round(team_profit, 2),
                    "won": team_won,
                    "lost": team_lost
                })

        # Sort daily by date, team_profits by profit descending
        daily_sorted = sorted(
            [{"date": k, **v} for k, v in daily_data.items()],
            key=lambda x: x["date"]
        )[-days:]

        team_profits_sorted = sorted(team_profits, key=lambda x: x["profit"], reverse=True)

        result = {
            "daily": daily_sorted,
            "team_profits": team_profits_sorted
        }

        google_sheets_client._set_cached(cache_key, result)
        return result

    except Exception as e:
        return {"daily": [], "team_profits": [], "error": str(e)}


@router.get("/bot/state", response_model=BotState)
async def get_bot_state():
    """Returnează starea curentă a botului."""
    return bot_engine.get_state()


@router.post("/bot/start", response_model=ApiResponse)
async def start_bot():
    """Pornește botul."""
    success = bot_engine.start()
    if success:
        return ApiResponse(success=True, message="Bot pornit cu succes")
    return ApiResponse(success=False, message="Botul rulează deja")


@router.post("/bot/stop", response_model=ApiResponse)
async def stop_bot():
    """Oprește botul."""
    success = bot_engine.stop()
    if success:
        return ApiResponse(success=True, message="Bot oprit cu succes")
    return ApiResponse(success=False, message="Botul este deja oprit")


@router.post("/bot/run-now", response_model=ApiResponse)
async def run_bot_now():
    """Execută un ciclu al botului imediat."""
    state = bot_engine.get_state()
    if state.status != BotStatus.RUNNING:
        return ApiResponse(success=False, message="Botul trebuie să fie pornit pentru a rula")

    result = await bot_engine.run_cycle()
    return ApiResponse(
        success=result["success"],
        message=result.get("message", "Ciclu executat"),
        data=result
    )


@router.get("/teams/search-betfair")
async def search_teams_betfair(q: str = ""):
    """
    Caută echipe pe Betfair API.
    Returnează lista de echipe găsite pentru autocomplete.
    """
    if len(q) < 3:
        return []

    from app.services.betfair_client import betfair_client
    import logging
    logger = logging.getLogger(__name__)

    try:
        if not betfair_client.is_connected():
            await betfair_client.connect()

        if not betfair_client.is_connected():
            return []

        events = await betfair_client.list_events(
            event_type_id="1",
            text_query=q
        )

        # Skip keywords pentru echipe rezerve/tineret
        skip_keywords = ["(Res)", "U19", "U21", "U23", "Women", "Feminin", "II", "B)", "(W)"]

        # Extragem numele unice ale echipelor din evenimente
        team_names = set()
        for event in events[:20]:
            event_name = event.get("event", {}).get("name", "")

            # Skip meciuri cu echipe rezerve/tineret
            if any(kw in event_name for kw in skip_keywords):
                continue

            # Evenimentele sunt "Team A v Team B"
            if " v " in event_name:
                parts = event_name.split(" v ")
                for part in parts:
                    part = part.strip()
                    # Filtram doar echipele care contin query-ul
                    if q.lower() in part.lower():
                        team_names.add(part)

        # Sortam alfabetic si returnam
        results = sorted(list(team_names))
        logger.info(f"Search Betfair '{q}': {len(results)} echipe găsite")
        return results

    except Exception as e:
        logger.error(f"Eroare căutare Betfair: {e}")
        return []


@router.get("/teams", response_model=List[Team])
async def get_teams(active_only: bool = False):
    """Returnează lista de echipe."""
    if active_only:
        return bot_engine.get_active_teams()
    return bot_engine.get_all_teams()


@router.get("/teams/{team_id}", response_model=Team)
async def get_team(team_id: str):
    """Returnează o echipă după ID."""
    team = bot_engine.get_team(team_id)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Echipa cu ID {team_id} nu a fost găsită"
        )
    return team


@router.post("/teams", response_model=Team, status_code=status.HTTP_201_CREATED)
async def create_team(team_create: TeamCreate):
    """Creează o echipă nouă și preia următoarele 20 de meciuri."""
    from app.services.google_sheets import google_sheets_client
    from app.services.betfair_client import betfair_client
    from app.config import get_settings
    import logging
    logger = logging.getLogger(__name__)

    settings = get_settings()
    initial_stake = team_create.initial_stake if team_create.initial_stake is not None else settings.bot_initial_stake

    team = Team(
        id=str(uuid4()),
        name=team_create.name,
        betfair_id=team_create.betfair_id,
        sport=team_create.sport,
        league=team_create.league,
        country=team_create.country,
        cumulative_loss=0.0,
        last_stake=0.0,
        progression_step=0,
        status=TeamStatus.ACTIVE,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    # Save to bot engine (memory)
    result = bot_engine.add_team(team)

    # Save to Google Sheets and fetch matches
    if not google_sheets_client.is_connected():
        google_sheets_client.connect()

    if google_sheets_client.is_connected():
        # Save team to Index sheet and create team sheet
        team_data = team.model_dump()
        team_data["initial_stake"] = initial_stake
        # Convert datetime to string for JSON serialization
        team_data["created_at"] = team_data["created_at"].isoformat() if team_data.get("created_at") else ""
        team_data["updated_at"] = team_data["updated_at"].isoformat() if team_data.get("updated_at") else ""
        google_sheets_client.save_team(team_data)

        # Fetch next 20 matches from Betfair with odds
        try:
            if not betfair_client.is_connected():
                await betfair_client.connect()

            if betfair_client.is_connected():
                # Search for team matches
                event_type_id = "1" if team.sport == "football" else "7522"
                events = await betfair_client.list_events(
                    event_type_id=event_type_id,
                    text_query=team.name
                )

                matches = []
                for event in events[:20]:
                    event_data = event.get("event", {})
                    event_id = event_data.get("id", "")
                    event_name = event_data.get("name", "")
                    competition = event.get("competitionName", "")

                    # Skip reserve/youth teams
                    skip_keywords = ["(Res)", "U19", "U21", "U23", "Women", "Feminin", "II", "B)", "(W)"]
                    if any(kw in event_name for kw in skip_keywords):
                        logger.info(f"Skip echipă rezerve/tineret: {event_name}")
                        continue

                    # Get odds and start time from market catalogue
                    odds = ""
                    market_start_time = ""
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
                                if market_start_time_utc:
                                    try:
                                        from datetime import datetime as dt
                                        import pytz
                                        utc_time = dt.fromisoformat(market_start_time_utc.replace("Z", "+00:00"))
                                        bucharest_tz = pytz.timezone("Europe/Bucharest")
                                        local_time = utc_time.astimezone(bucharest_tz)
                                        market_start_time = local_time.strftime("%Y-%m-%dT%H:%M")
                                    except:
                                        market_start_time = market_start_time_utc
                                else:
                                    market_start_time = ""

                                if market_id:
                                    # Get runner prices
                                    prices = await betfair_client.list_market_book([market_id])
                                    if prices and prices[0].get("runners"):
                                        price_runners = prices[0].get("runners", [])
                                        market_runners = market.get("runners", [])

                                        # Găsim runner-ul echipei noastre (nu primul runner!)
                                        team_selection_id = None
                                        for mr in market_runners:
                                            runner_name = mr.get("runnerName", "")
                                            if team.name.lower() in runner_name.lower():
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
                                            # Fallback: dacă nu găsim, luăm primul runner
                                            if price_runners:
                                                back_prices = price_runners[0].get("ex", {}).get("availableToBack", [])
                                                if back_prices:
                                                    odds = back_prices[0].get("price", "")
                        except Exception as e:
                            logger.warning(f"Could not get odds for {event_name}: {e}")

                    matches.append({
                        "start_time": market_start_time,
                        "event_name": event_name,
                        "competition": competition,
                        "odds": str(odds) if odds else ""
                    })

                if matches:
                    # Sortare meciuri cronologic după start_time
                    matches_sorted = sorted(matches, key=lambda x: x.get("start_time", ""))
                    google_sheets_client.save_matches_for_team(team.name, matches_sorted)
                    logger.info(f"Saved {len(matches_sorted)} matches for {team.name} (sorted by date)")
                else:
                    logger.warning(f"No matches found for {team.name}")

        except Exception as e:
            logger.error(f"Error fetching matches for {team.name}: {e}")

    return result


@router.put("/teams/{team_id}", response_model=Team)
async def update_team(team_id: str, team_update: TeamUpdate):
    """Actualizează o echipă."""
    updates = team_update.model_dump(exclude_unset=True)
    team = bot_engine.update_team(team_id, updates)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Echipa cu ID {team_id} nu a fost găsită"
        )
    return team


@router.delete("/teams/{team_id}", response_model=ApiResponse)
async def delete_team(team_id: str):
    """Șterge o echipă."""
    success = bot_engine.delete_team(team_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Echipa cu ID {team_id} nu a fost găsită"
        )
    return ApiResponse(success=True, message="Echipă ștearsă cu succes")


@router.post("/teams/{team_id}/pause", response_model=Team)
async def pause_team(team_id: str):
    """Pune o echipă pe pauză."""
    team = bot_engine.update_team(team_id, {"status": TeamStatus.PAUSED})
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Echipa cu ID {team_id} nu a fost găsită"
        )
    return team


@router.post("/teams/{team_id}/activate", response_model=Team)
async def activate_team(team_id: str):
    """Activează o echipă."""
    team = bot_engine.update_team(team_id, {"status": TeamStatus.ACTIVE})
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Echipa cu ID {team_id} nu a fost găsită"
        )
    return team


@router.post("/teams/{team_id}/reset", response_model=Team)
async def reset_team_progression(team_id: str):
    """Resetează progresia unei echipe."""
    team = bot_engine.reset_team_progression(team_id)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Echipa cu ID {team_id} nu a fost găsită"
        )
    return team


@router.get("/teams/{team_id}/progression")
async def get_team_progression(team_id: str, next_odds: float = 1.5):
    """Returnează informații despre progresia unei echipe."""
    team = bot_engine.get_team(team_id)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Echipa cu ID {team_id} nu a fost găsită"
        )

    return staking_service.get_progression_info(
        team.cumulative_loss,
        team.progression_step,
        next_odds
    )


@router.put("/teams/{team_id}/initial-stake")
async def update_team_initial_stake(team_id: str, initial_stake: float):
    """Actualizează miza inițială pentru o echipă."""
    from app.services.google_sheets import google_sheets_client

    team = bot_engine.get_team(team_id)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Echipa cu ID {team_id} nu a fost găsită"
        )

    if initial_stake <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Miza inițială trebuie să fie > 0"
        )

    if not google_sheets_client.is_connected():
        google_sheets_client.connect()

    success = google_sheets_client.update_team_initial_stake(team.name, initial_stake)

    if success:
        return {"success": True, "message": f"Miză inițială actualizată: {initial_stake} RON"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Eroare la actualizarea mizei inițiale"
        )


@router.get("/bets", response_model=List[Bet])
async def get_bets(
    team_id: Optional[str] = None,
    status_filter: Optional[BetStatus] = None,
    limit: int = 100
):
    """Returnează lista de pariuri."""
    bets = bot_engine.get_all_bets()

    if team_id:
        bets = [b for b in bets if b.team_id == team_id]

    if status_filter:
        bets = [b for b in bets if b.status == status_filter]

    bets.sort(key=lambda b: b.created_at, reverse=True)

    return bets[:limit]


@router.get("/bets/pending", response_model=List[Bet])
async def get_pending_bets():
    """Returnează pariurile în așteptare."""
    return bot_engine.get_pending_bets()


@router.get("/bets/{bet_id}", response_model=Bet)
async def get_bet(bet_id: str):
    """Returnează un pariu după ID."""
    bet = bot_engine.get_bet(bet_id)
    if not bet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pariul cu ID {bet_id} nu a fost găsit"
        )
    return bet


@router.post("/bets/{bet_id}/settle", response_model=Bet)
async def settle_bet(bet_id: str, won: bool):
    """Marchează un pariu ca câștigat sau pierdut."""
    bet = bot_engine.get_bet(bet_id)
    if not bet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pariul cu ID {bet_id} nu a fost găsit"
        )

    if bet.status not in [BetStatus.PLACED, BetStatus.MATCHED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Pariul nu poate fi finalizat, status curent: {bet.status}"
        )

    bot_engine.process_bet_result(bet, won)
    return bot_engine.get_bet(bet_id)


@router.get("/calculate-stake")
async def calculate_stake(
    cumulative_loss: float = 0,
    odds: float = 1.5,
    progression_step: int = 0
):
    """Calculează miza pentru parametrii dați."""
    if odds <= 1.0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cota trebuie să fie mai mare decât 1.0"
        )

    stake, stop_loss = staking_service.calculate_stake(
        cumulative_loss, odds, progression_step
    )

    potential_profit = 0.0
    if not stop_loss:
        potential_profit = staking_service.calculate_potential_profit(stake, odds)

    return {
        "stake": stake,
        "potential_profit": potential_profit,
        "stop_loss_reached": stop_loss,
        "cumulative_loss": cumulative_loss,
        "odds": odds,
        "progression_step": progression_step
    }


@router.get("/settings", response_model=AppSettings)
async def get_settings():
    """Returnează setările aplicației."""
    return settings_manager.get_settings()


@router.put("/settings", response_model=AppSettings)
async def update_settings(updates: SettingsUpdate):
    """Actualizează setările aplicației."""
    updated = settings_manager.update_settings(updates)

    if updates.initial_stake:
        staking_service.initial_stake = updates.initial_stake
    if updates.max_progression_steps:
        staking_service.max_progression_steps = updates.max_progression_steps

    # Update scheduler if time changed
    if updates.bot_run_hour is not None or updates.bot_run_minute is not None:
        from app.main import scheduler, scheduled_bot_run
        import pytz
        from apscheduler.triggers.cron import CronTrigger

        timezone = pytz.timezone("Europe/Bucharest")
        new_hour = updates.bot_run_hour if updates.bot_run_hour is not None else updated.bot_run_hour
        new_minute = updates.bot_run_minute if updates.bot_run_minute is not None else updated.bot_run_minute

        trigger = CronTrigger(
            hour=new_hour,
            minute=new_minute,
            timezone=timezone
        )

        # Remove old job and add new one
        try:
            scheduler.remove_job("daily_bot_run")
        except:
            pass

        scheduler.add_job(
            scheduled_bot_run,
            trigger=trigger,
            id="daily_bot_run",
            name="Execuție zilnică bot",
            replace_existing=True
        )

        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Scheduler reprogramat la {new_hour:02d}:{new_minute:02d}")

    return updated


@router.get("/settings/betfair-status")
async def get_betfair_status():
    """Returnează statusul conexiunii Betfair."""
    return {
        "connected": betfair_client.is_connected(),
        "configured": True  # Always true since auto-configured from .env
    }


@router.post("/settings/test-betfair", response_model=ApiResponse)
async def test_betfair_connection():
    """Testează conexiunea la Betfair API."""
    # Try to connect if not already connected
    if not betfair_client.is_connected():
        connected = await betfair_client.connect()
    else:
        connected = True

    if connected:
        return ApiResponse(success=True, message="Conectat la Betfair API")
    else:
        return ApiResponse(success=False, message="Conexiune eșuată la Betfair API")


@router.post("/settings/test-google-sheets", response_model=ApiResponse)
async def test_google_sheets_connection():
    """Testează conexiunea la Google Sheets."""
    from app.config import get_settings

    app_settings = get_settings()
    settings = settings_manager.get_settings()

    if not settings_manager.is_google_sheets_configured():
        return ApiResponse(
            success=False,
            message="Google Sheets nu este configurat"
        )

    google_sheets_client.configure(
        spreadsheet_id=settings.google_sheets_spreadsheet_id,
        credentials_path=app_settings.google_sheets_credentials_path
    )

    connected = google_sheets_client.connect()
    settings_manager.set_google_sheets_connected(connected)

    if connected:
        return ApiResponse(success=True, message="Conectat la Google Sheets")
    else:
        return ApiResponse(success=False, message="Conexiune eșuată la Google Sheets")


# AI Chat endpoints
from app.services.ai_chat import ai_chat


class ChatRequest(BaseModel):
    message: str
    use_betfair: bool = True


class ChatResponse(BaseModel):
    response: str


@router.post("/ai/chat", response_model=ChatResponse)
async def ai_chat_endpoint(request: ChatRequest):
    """Trimite un mesaj către AI și primește răspuns cu date live de pe Betfair."""
    if request.use_betfair:
        # Use chat_with_bets which handles both bets queries and match queries
        response = await ai_chat.chat_with_bets(request.message)
    else:
        response = await ai_chat.chat(request.message)
    return ChatResponse(response=response)


@router.post("/ai/clear")
async def clear_ai_chat():
    """Șterge istoricul conversației AI."""
    ai_chat.clear_history()
    return {"success": True, "message": "Istoric șters"}


@router.post("/sheets/apply-formatting")
async def apply_sheets_formatting(username: str = Depends(get_current_user)):
    """Aplică conditional formatting pe toate sheet-urile echipelor."""
    count = google_sheets_client.apply_formatting_to_all_teams()
    return {"success": True, "sheets_updated": count}


@router.get("/logs")
async def get_logs(lines: int = 100):
    """Returnează ultimele N linii din logs."""
    import subprocess
    try:
        result = subprocess.run(
            ["journalctl", "-u", "betfair-bot", "-n", str(lines), "--no-pager"],
            capture_output=True,
            text=True,
            timeout=10
        )
        log_lines = result.stdout.strip().split("\n") if result.stdout else []
        return {"success": True, "logs": log_lines}
    except Exception as e:
        return {"success": False, "logs": [], "error": str(e)}
