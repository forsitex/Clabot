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
    """Creează o echipă nouă."""
    team = Team(
        id=str(uuid4()),
        name=team_create.name,
        betfair_id=team_create.betfair_id,
        sport=team_create.sport,
        league=team_create.league,
        country=team_create.country,
        cumulative_loss=0.0,
        last_stake=100.0,
        progression_step=0,
        status=TeamStatus.ACTIVE,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    return bot_engine.add_team(team)


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

    return updated


@router.post("/settings/test-betfair", response_model=ApiResponse)
async def test_betfair_connection():
    """Testează conexiunea la Betfair API."""
    settings = settings_manager.get_settings()

    if not settings_manager.is_betfair_configured():
        return ApiResponse(
            success=False,
            message="Credențialele Betfair nu sunt configurate"
        )

    betfair_client.configure(
        app_key=settings.betfair_app_key,
        username=settings.betfair_username,
        password=settings.betfair_password
    )

    connected = await betfair_client.connect()
    settings_manager.set_betfair_connected(connected)

    if connected:
        return ApiResponse(success=True, message="Conectat la Betfair API")
    else:
        return ApiResponse(success=False, message="Conexiune eșuată la Betfair API")


@router.post("/settings/test-google-sheets", response_model=ApiResponse)
async def test_google_sheets_connection():
    """Testează conexiunea la Google Sheets."""
    settings = settings_manager.get_settings()

    if not settings_manager.is_google_sheets_configured():
        return ApiResponse(
            success=False,
            message="Google Sheets nu este configurat"
        )

    google_sheets_client.configure(
        spreadsheet_id=settings.google_sheets_spreadsheet_id
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
        response = await ai_chat.chat_with_betfair(request.message)
    else:
        response = await ai_chat.chat(request.message)
    return ChatResponse(response=response)


@router.post("/ai/clear")
async def clear_ai_chat():
    """Șterge istoricul conversației AI."""
    ai_chat.clear_history()
    return {"success": True, "message": "Istoric șters"}
