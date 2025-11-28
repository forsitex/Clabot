from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class TeamStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"


class BetStatus(str, Enum):
    PENDING = "pending"
    PLACED = "placed"
    MATCHED = "matched"
    WON = "won"
    LOST = "lost"
    VOID = "void"
    ERROR = "error"


class BotStatus(str, Enum):
    STOPPED = "stopped"
    RUNNING = "running"
    ERROR = "error"


class Sport(str, Enum):
    FOOTBALL = "football"
    BASKETBALL = "basketball"


class Team(BaseModel):
    id: str = Field(..., description="Unique team identifier")
    name: str = Field(..., description="Team name")
    betfair_id: Optional[str] = Field(None, description="Betfair selection ID")
    sport: Sport = Field(..., description="Sport type")
    league: str = Field(..., description="League/Competition name")
    country: str = Field(..., description="Country code")
    cumulative_loss: float = Field(default=0.0, ge=0, description="Cumulative loss in RON")
    last_stake: float = Field(default=100.0, gt=0, description="Last stake placed")
    progression_step: int = Field(default=0, ge=0, description="Current progression step")
    status: TeamStatus = Field(default=TeamStatus.ACTIVE, description="Team status")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TeamCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    betfair_id: Optional[str] = None
    sport: Sport
    league: str = Field(..., min_length=1, max_length=100)
    country: str = Field(..., min_length=2, max_length=50)


class TeamUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    betfair_id: Optional[str] = None
    sport: Optional[Sport] = None
    league: Optional[str] = Field(None, min_length=1, max_length=100)
    country: Optional[str] = Field(None, min_length=2, max_length=50)
    status: Optional[TeamStatus] = None


class Bet(BaseModel):
    id: str = Field(..., description="Unique bet identifier")
    team_id: str = Field(..., description="Reference to team")
    team_name: str = Field(..., description="Team name for display")
    event_name: str = Field(..., description="Match name (e.g., Liverpool vs Chelsea)")
    event_id: Optional[str] = Field(None, description="Betfair event ID")
    market_id: Optional[str] = Field(None, description="Betfair market ID")
    selection_id: Optional[str] = Field(None, description="Betfair selection ID")
    bet_id: Optional[str] = Field(None, description="Betfair bet ID after placement")
    pronostic: int = Field(..., ge=1, le=2, description="1 for home win, 2 for away win")
    odds: float = Field(..., gt=1.0, description="Odds at placement")
    stake: float = Field(..., gt=0, description="Stake amount in RON")
    potential_profit: float = Field(..., description="Potential profit if won")
    result: Optional[float] = Field(None, description="Actual profit/loss after settlement")
    status: BetStatus = Field(default=BetStatus.PENDING)
    placed_at: Optional[datetime] = Field(None, description="When bet was placed")
    settled_at: Optional[datetime] = Field(None, description="When bet was settled")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class BetCreate(BaseModel):
    team_id: str
    event_name: str
    event_id: Optional[str] = None
    market_id: Optional[str] = None
    selection_id: Optional[str] = None
    pronostic: int = Field(..., ge=1, le=2)
    odds: float = Field(..., gt=1.0)
    stake: float = Field(..., gt=0)


class Match(BaseModel):
    event_id: str = Field(..., description="Betfair event ID")
    event_name: str = Field(..., description="Match name")
    market_id: str = Field(..., description="Betfair market ID for Match Odds")
    competition_id: str = Field(..., description="Competition/League ID")
    competition_name: str = Field(..., description="Competition/League name")
    start_time: datetime = Field(..., description="Match start time")
    home_team: str = Field(..., description="Home team name")
    away_team: str = Field(..., description="Away team name")
    home_selection_id: str = Field(..., description="Betfair selection ID for home team")
    away_selection_id: str = Field(..., description="Betfair selection ID for away team")
    draw_selection_id: str = Field(..., description="Betfair selection ID for draw")
    home_odds: Optional[float] = Field(None, description="Current back odds for home")
    away_odds: Optional[float] = Field(None, description="Current back odds for away")
    draw_odds: Optional[float] = Field(None, description="Current back odds for draw")
    total_matched: float = Field(default=0.0, description="Total amount matched on market")


class BotState(BaseModel):
    status: BotStatus = Field(default=BotStatus.STOPPED)
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    last_error: Optional[str] = None
    bets_placed_today: int = Field(default=0)
    total_stake_today: float = Field(default=0.0)


class DashboardStats(BaseModel):
    total_teams: int = Field(default=0)
    active_teams: int = Field(default=0)
    total_bets: int = Field(default=0)
    won_bets: int = Field(default=0)
    lost_bets: int = Field(default=0)
    pending_bets: int = Field(default=0)
    total_profit: float = Field(default=0.0)
    win_rate: float = Field(default=0.0)
    total_staked: float = Field(default=0.0)


class PlaceOrderRequest(BaseModel):
    market_id: str
    selection_id: str
    side: str = Field(default="BACK")
    order_type: str = Field(default="LIMIT")
    size: float = Field(..., gt=0)
    price: float = Field(..., gt=1.0)
    persistence_type: str = Field(default="LAPSE")


class PlaceOrderResponse(BaseModel):
    success: bool
    bet_id: Optional[str] = None
    status: str
    size_matched: float = Field(default=0.0)
    average_price_matched: float = Field(default=0.0)
    placed_date: Optional[datetime] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None


class ApiResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None
