import { defineStore } from "pinia";
import { ref } from "vue";

export const useLogsStore = defineStore("logs", () => {
  const logs = ref<string[]>([]);
  const isLive = ref(false);
  const isLoading = ref(false);
  let intervalId: number | null = null;

  function clearLogs() {
    logs.value = [];
  }

  async function fetchLogs() {
    isLoading.value = true;
    try {
      const response = await fetch("/api/logs?lines=200");
      const data = await response.json();
      if (data.success && data.logs) {
        logs.value = data.logs;
      }
    } catch (error) {
      logs.value = [`[Error fetching logs: ${error}]`];
    } finally {
      isLoading.value = false;
    }
  }

  function startLive() {
    if (intervalId) return;

    fetchLogs();
    intervalId = window.setInterval(fetchLogs, 5000);
    isLive.value = true;
  }

  function stopLive() {
    if (intervalId) {
      clearInterval(intervalId);
      intervalId = null;
    }
    isLive.value = false;
  }

  return {
    logs,
    isLive,
    isLoading,
    clearLogs,
    fetchLogs,
    startLive,
    stopLive,
  };
});
