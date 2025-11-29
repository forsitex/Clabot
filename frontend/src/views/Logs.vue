<template>
  <div class="p-6">
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-2xl font-bold">Logs Backend</h1>
      <div class="flex gap-2">
        <button
          @click="toggleLive"
          :class="[
            'px-4 py-2 rounded',
            logsStore.isLive
              ? 'bg-red-500 hover:bg-red-600'
              : 'bg-green-500 hover:bg-green-600',
            'text-white',
          ]"
        >
          {{ logsStore.isLive ? "Stop Live" : "Start Live" }}
        </button>
        <button
          @click="clearLogs"
          class="px-4 py-2 bg-gray-500 hover:bg-gray-600 text-white rounded"
        >
          Clear
        </button>
      </div>
    </div>

    <div
      class="bg-black text-green-400 p-4 rounded font-mono text-sm h-[calc(100vh-200px)] overflow-y-auto"
    >
      <div
        v-for="(log, index) in logsStore.logs"
        :key="index"
        class="whitespace-pre-wrap"
      >
        {{ log }}
      </div>
      <div v-if="logsStore.logs.length === 0" class="text-gray-500">
        No logs yet. Click "Start Live" to begin streaming.
      </div>
    </div>
  </div>
</template>

<script setup>
import { watch, nextTick } from "vue";
import { useLogsStore } from "@/stores/logs";

const logsStore = useLogsStore();

const toggleLive = () => {
  if (logsStore.isLive) {
    logsStore.stopLive();
  } else {
    logsStore.startLive();
  }
};

const clearLogs = () => {
  logsStore.clearLogs();
};

// Auto-scroll to bottom when new logs arrive
watch(
  () => logsStore.logs.length,
  () => {
    nextTick(() => {
      const container = document.querySelector(".overflow-y-auto");
      if (container) {
        container.scrollTop = container.scrollHeight;
      }
    });
  }
);
</script>
