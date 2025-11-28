from fastapi import APIRouter, HTTPException, status
from typing import List, Optional
from uuid import uuid4
from datetime import datetime

from app.models.schemas import (
    Team, TeamCreate, TeamUpdate, TeamStatus,
    Bet, BetStatus,
    BotState, BotStatus,
    DashboardStats, ApiResponse, Sport
)
from app.services.bot_engine import bot_engine
from app.services.staking import staking_service

router = APIRouter()


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
