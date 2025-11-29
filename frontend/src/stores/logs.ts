import { defineStore } from "pinia";
import { ref } from "vue";

export const useLogsStore = defineStore("logs", () => {
  const logs = ref<string[]>([]);
  const isLive = ref(false);
  let ws: WebSocket | null = null;

  function addLog(log: string) {
    logs.value.push(log);
    
    // Keep only last 1000 logs to avoid memory issues
    if (logs.value.length > 1000) {
      logs.value = logs.value.slice(-1000);
    }
  }

  function clearLogs() {
    logs.value = [];
  }

  function startLive() {
    if (ws) {
      return; // Already connected
    }

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/api/ws/logs`;

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      isLive.value = true;
      addLog("[Connected to live logs]");
    };

    ws.onmessage = (event) => {
      addLog(event.data);
    };

    ws.onerror = (error) => {
      addLog(`[Error: ${error}]`);
    };

    ws.onclose = () => {
      isLive.value = false;
      addLog("[Disconnected from live logs]");
      ws = null;
    };
  }

  function stopLive() {
    if (ws) {
      ws.close();
      ws = null;
    }
    isLive.value = false;
  }

  return {
    logs,
    isLive,
    addLog,
    clearLogs,
    startLive,
    stopLive,
  };
});
