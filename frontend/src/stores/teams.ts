import { defineStore } from "pinia";
import { ref, computed } from "vue";
import type { Team, TeamCreate, TeamUpdate } from "@/types";
import * as api from "@/services/api";

export const useTeamsStore = defineStore("teams", () => {
  const teams = ref<Team[]>([]);
  const isLoading = ref(false);
  const error = ref<string | null>(null);

  const activeTeams = computed(() =>
    teams.value.filter((t) => t.status === "active")
  );
  const pausedTeams = computed(() =>
    teams.value.filter((t) => t.status === "paused")
  );
  const totalTeams = computed(() => teams.value.length);

  async function fetchTeams(activeOnly = false): Promise<void> {
    isLoading.value = true;
    error.value = null;
    try {
      teams.value = await api.getTeams(activeOnly);
    } catch (e) {
      error.value =
        e instanceof Error ? e.message : "Eroare la încărcarea echipelor";
    } finally {
      isLoading.value = false;
    }
  }

  async function createTeam(teamData: TeamCreate): Promise<Team | null> {
    isLoading.value = true;
    error.value = null;
    try {
      const newTeam = await api.createTeam(teamData);
      teams.value.push(newTeam);
      return newTeam;
    } catch (e) {
      error.value =
        e instanceof Error ? e.message : "Eroare la crearea echipei";
      return null;
    } finally {
      isLoading.value = false;
    }
  }

  async function updateTeam(
    teamId: string,
    updates: TeamUpdate
  ): Promise<Team | null> {
    isLoading.value = true;
    error.value = null;
    try {
      const updatedTeam = await api.updateTeam(teamId, updates);
      const index = teams.value.findIndex((t) => t.id === teamId);
      if (index !== -1) {
        teams.value[index] = updatedTeam;
      }
      return updatedTeam;
    } catch (e) {
      error.value =
        e instanceof Error ? e.message : "Eroare la actualizarea echipei";
      return null;
    } finally {
      isLoading.value = false;
    }
  }

  async function deleteTeam(teamId: string): Promise<boolean> {
    isLoading.value = true;
    error.value = null;
    try {
      await api.deleteTeam(teamId);
      teams.value = teams.value.filter((t) => t.id !== teamId);
      return true;
    } catch (e) {
      error.value =
        e instanceof Error ? e.message : "Eroare la ștergerea echipei";
      return false;
    } finally {
      isLoading.value = false;
    }
  }

  async function pauseTeam(teamId: string): Promise<boolean> {
    try {
      const updatedTeam = await api.pauseTeam(teamId);
      const index = teams.value.findIndex((t) => t.id === teamId);
      if (index !== -1) {
        teams.value[index] = updatedTeam;
      }
      return true;
    } catch (e) {
      error.value =
        e instanceof Error ? e.message : "Eroare la punerea pe pauză";
      return false;
    }
  }

  async function activateTeam(teamId: string): Promise<boolean> {
    try {
      const updatedTeam = await api.activateTeam(teamId);
      const index = teams.value.findIndex((t) => t.id === teamId);
      if (index !== -1) {
        teams.value[index] = updatedTeam;
      }
      return true;
    } catch (e) {
      error.value =
        e instanceof Error ? e.message : "Eroare la activarea echipei";
      return false;
    }
  }

  async function resetProgression(teamId: string): Promise<boolean> {
    try {
      const updatedTeam = await api.resetTeamProgression(teamId);
      const index = teams.value.findIndex((t) => t.id === teamId);
      if (index !== -1) {
        teams.value[index] = updatedTeam;
      }
      return true;
    } catch (e) {
      error.value =
        e instanceof Error ? e.message : "Eroare la resetarea progresiei";
      return false;
    }
  }

  function getTeamById(teamId: string): Team | undefined {
    return teams.value.find((t) => t.id === teamId);
  }

  function updateTeamFromWs(team: Team): void {
    const index = teams.value.findIndex((t) => t.id === team.id);
    if (index !== -1) {
      teams.value[index] = team;
    } else {
      teams.value.push(team);
    }
  }

  return {
    teams,
    isLoading,
    error,
    activeTeams,
    pausedTeams,
    totalTeams,
    fetchTeams,
    createTeam,
    updateTeam,
    deleteTeam,
    pauseTeam,
    activateTeam,
    resetProgression,
    getTeamById,
    updateTeamFromWs,
  };
});
