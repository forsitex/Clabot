export interface Team {
  id: string;
  name: string;
  betfair_id: string | null;
  sport: "football" | "basketball";
  league: string;
  country: string;
  cumulative_loss: number;
  last_stake: number;
  progression_step: number;
  status: "active" | "paused";
  total_matches: number;
  matches_won: number;
  matches_lost: number;
  total_profit: number;
  created_at: string;
  updated_at: string;
}

export interface TeamCreate {
  name: string;
  betfair_id?: string;
  sport: "football" | "basketball";
  league: string;
  country: string;
}

export interface TeamUpdate {
  name?: string;
  betfair_id?: string;
  sport?: "football" | "basketball";
  league?: string;
  country?: string;
  status?: "active" | "paused";
}

export interface Bet {
  id: string;
  team_id: string;
  team_name: string;
  event_name: string;
  event_id: string | null;
  market_id: string | null;
  selection_id: string | null;
  bet_id: string | null;
  pronostic: 1 | 2;
  odds: number;
  stake: number;
  potential_profit: number;
  result: number | null;
  status: "pending" | "placed" | "matched" | "won" | "lost" | "void" | "error";
  placed_at: string | null;
  settled_at: string | null;
  created_at: string;
}

export interface BotState {
  status: "stopped" | "running" | "error";
  last_run: string | null;
  next_run: string | null;
  last_error: string | null;
  bets_placed_today: number;
  total_stake_today: number;
}

export interface DashboardStats {
  total_teams: number;
  active_teams: number;
  total_bets: number;
  won_bets: number;
  lost_bets: number;
  pending_bets: number;
  total_profit: number;
  win_rate: number;
  total_staked: number;
}

export interface ProgressionInfo {
  cumulative_loss: number;
  progression_step: number;
  max_progression_steps: number;
  next_stake: number;
  next_odds: number;
  potential_profit: number;
  stop_loss_reached: boolean;
  initial_stake: number;
}

export interface ApiResponse<T = unknown> {
  success: boolean;
  message: string;
  data?: T;
}

export interface WebSocketMessage {
  type: string;
  data?: unknown;
  timestamp: string;
  message?: string;
  level?: "info" | "success" | "warning" | "error";
}
