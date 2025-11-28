import { defineStore } from "pinia";
import { ref, computed } from "vue";
import type { BotState, DashboardStats } from "@/types";
import * as api from "@/services/api";

export const useBotStore = defineStore("bot", () => {
  const state = ref<BotState>({
    status: "stopped",
    last_run: null,
    next_run: null,
    last_error: null,
    bets_placed_today: 0,
    total_stake_today: 0,
  });

  const stats = ref<DashboardStats>({
    total_teams: 0,
    active_teams: 0,
    total_bets: 0,
    won_bets: 0,
    lost_bets: 0,
    pending_bets: 0,
    total_profit: 0,
    win_rate: 0,
    total_staked: 0,
  });

  const isLoading = ref(false);
  const error = ref<string | null>(null);

  const isRunning = computed(() => state.value.status === "running");
  const isStopped = computed(() => state.value.status === "stopped");
  const hasError = computed(() => state.value.status === "error");

  async function fetchState(): Promise<void> {
    try {
      state.value = await api.getBotState();
    } catch (e) {
      error.value =
        e instanceof Error ? e.message : "Eroare la încărcarea stării";
    }
  }

  async function fetchStats(): Promise<void> {
    try {
      stats.value = await api.getStats();
    } catch (e) {
      error.value =
        e instanceof Error ? e.message : "Eroare la încărcarea statisticilor";
    }
  }

  async function start(): Promise<boolean> {
    isLoading.value = true;
    error.value = null;
    try {
      const response = await api.startBot();
      if (response.success) {
        await fetchState();
      }
      return response.success;
    } catch (e) {
      error.value =
        e instanceof Error ? e.message : "Eroare la pornirea botului";
      return false;
    } finally {
      isLoading.value = false;
    }
  }

  async function stop(): Promise<boolean> {
    isLoading.value = true;
    error.value = null;
    try {
      const response = await api.stopBot();
      if (response.success) {
        await fetchState();
      }
      return response.success;
    } catch (e) {
      error.value =
        e instanceof Error ? e.message : "Eroare la oprirea botului";
      return false;
    } finally {
      isLoading.value = false;
    }
  }

  async function runNow(): Promise<boolean> {
    isLoading.value = true;
    error.value = null;
    try {
      const response = await api.runBotNow();
      await fetchState();
      await fetchStats();
      return response.success;
    } catch (e) {
      error.value =
        e instanceof Error ? e.message : "Eroare la execuția botului";
      return false;
    } finally {
      isLoading.value = false;
    }
  }

  function updateState(newState: BotState): void {
    state.value = newState;
  }

  function updateStats(newStats: DashboardStats): void {
    stats.value = newStats;
  }

  return {
    state,
    stats,
    isLoading,
    error,
    isRunning,
    isStopped,
    hasError,
    fetchState,
    fetchStats,
    start,
    stop,
    runNow,
    updateState,
    updateStats,
  };
});
