import axios from "axios";
import type {
  Team,
  TeamCreate,
  TeamUpdate,
  Bet,
  BotState,
  DashboardStats,
  ProgressionInfo,
  ApiResponse,
} from "@/types";

const api = axios.create({
  baseURL: "/api",
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("auth_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("auth_token");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

export const healthCheck = async (): Promise<{
  status: string;
  timestamp: string;
}> => {
  const response = await api.get("/health");
  return response.data;
};

export const getStats = async (): Promise<DashboardStats> => {
  const response = await api.get("/stats");
  return response.data;
};

export const getBotState = async (): Promise<BotState> => {
  const response = await api.get("/bot/state");
  return response.data;
};

export const startBot = async (): Promise<ApiResponse> => {
  const response = await api.post("/bot/start");
  return response.data;
};

export const stopBot = async (): Promise<ApiResponse> => {
  const response = await api.post("/bot/stop");
  return response.data;
};

export const runBotNow = async (): Promise<ApiResponse> => {
  const response = await api.post("/bot/run-now");
  return response.data;
};

export const searchTeamsBetfair = async (query: string): Promise<string[]> => {
  if (query.length < 3) return [];
  const response = await api.get("/teams/search-betfair", {
    params: { q: query },
  });
  return response.data;
};

export const getTeams = async (activeOnly = false): Promise<Team[]> => {
  const response = await api.get("/teams", {
    params: { active_only: activeOnly },
  });
  return response.data;
};

export const getTeam = async (teamId: string): Promise<Team> => {
  const response = await api.get(`/teams/${teamId}`);
  return response.data;
};

export const createTeam = async (team: TeamCreate): Promise<Team> => {
  const response = await api.post("/teams", team);
  return response.data;
};

export const updateTeam = async (
  teamId: string,
  updates: TeamUpdate
): Promise<Team> => {
  const response = await api.put(`/teams/${teamId}`, updates);
  return response.data;
};

export const deleteTeam = async (teamId: string): Promise<ApiResponse> => {
  const response = await api.delete(`/teams/${teamId}`);
  return response.data;
};

export const pauseTeam = async (teamId: string): Promise<Team> => {
  const response = await api.post(`/teams/${teamId}/pause`);
  return response.data;
};

export const activateTeam = async (teamId: string): Promise<Team> => {
  const response = await api.post(`/teams/${teamId}/activate`);
  return response.data;
};

export const updateTeamInitialStake = async (
  teamId: string,
  initialStake: number
): Promise<ApiResponse> => {
  const response = await api.put(`/teams/${teamId}/initial-stake`, null, {
    params: { initial_stake: initialStake },
  });
  return response.data;
};

export const resetTeamProgression = async (teamId: string): Promise<Team> => {
  const response = await api.post(`/teams/${teamId}/reset`);
  return response.data;
};

export const getTeamProgression = async (
  teamId: string,
  nextOdds = 1.5
): Promise<ProgressionInfo> => {
  const response = await api.get(`/teams/${teamId}/progression`, {
    params: { next_odds: nextOdds },
  });
  return response.data;
};

export const getBets = async (params?: {
  team_id?: string;
  status_filter?: string;
  limit?: number;
}): Promise<Bet[]> => {
  const response = await api.get("/bets", { params });
  return response.data;
};

export const getPendingBets = async (): Promise<Bet[]> => {
  const response = await api.get("/bets/pending");
  return response.data;
};

export const getBet = async (betId: string): Promise<Bet> => {
  const response = await api.get(`/bets/${betId}`);
  return response.data;
};

export const settleBet = async (betId: string, won: boolean): Promise<Bet> => {
  const response = await api.post(`/bets/${betId}/settle`, null, {
    params: { won },
  });
  return response.data;
};

export const calculateStake = async (
  cumulativeLoss: number,
  odds: number,
  progressionStep: number
): Promise<{
  stake: number;
  potential_profit: number;
  stop_loss_reached: boolean;
  cumulative_loss: number;
  odds: number;
  progression_step: number;
}> => {
  const response = await api.get("/calculate-stake", {
    params: {
      cumulative_loss: cumulativeLoss,
      odds,
      progression_step: progressionStep,
    },
  });
  return response.data;
};

export interface AppSettings {
  betfair_app_key: string;
  betfair_username: string;
  betfair_password: string;
  betfair_cert_file: string | null;
  betfair_key_file: string | null;
  google_sheets_spreadsheet_id: string;
  google_credentials_file: string | null;
  bot_run_hour: number;
  bot_run_minute: number;
  initial_stake: number;
  max_progression_steps: number;
  betfair_connected: boolean;
  google_sheets_connected: boolean;
}

export interface SettingsUpdate {
  betfair_app_key?: string;
  betfair_username?: string;
  betfair_password?: string;
  google_sheets_spreadsheet_id?: string;
  bot_run_hour?: number;
  bot_run_minute?: number;
  initial_stake?: number;
  max_progression_steps?: number;
}

export const getSettings = async (): Promise<AppSettings> => {
  const response = await api.get("/settings");
  return response.data;
};

export const updateSettings = async (
  updates: SettingsUpdate
): Promise<AppSettings> => {
  const response = await api.put("/settings", updates);
  return response.data;
};

export const getBetfairStatus = async (): Promise<{
  connected: boolean;
  configured: boolean;
}> => {
  const response = await api.get("/settings/betfair-status");
  return response.data;
};

export const testBetfairConnection = async (): Promise<ApiResponse> => {
  const response = await api.post("/settings/test-betfair");
  return response.data;
};

export const testGoogleSheetsConnection = async (): Promise<ApiResponse> => {
  const response = await api.post("/settings/test-google-sheets");
  return response.data;
};

export default api;
