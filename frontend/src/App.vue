<script setup lang="ts">
import { onMounted, onUnmounted } from "vue";
import { RouterView, RouterLink, useRoute } from "vue-router";
import { LayoutDashboard, Users, History, Settings } from "lucide-vue-next";
import { useBotStore } from "@/stores/bot";
import { useTeamsStore } from "@/stores/teams";
import { useWebSocket } from "@/services/websocket";
import type { WebSocketMessage } from "@/types";

const route = useRoute();
const botStore = useBotStore();
const teamsStore = useTeamsStore();

function handleWebSocketMessage(message: WebSocketMessage): void {
  switch (message.type) {
    case "bot_state":
      botStore.updateState(message.data as any);
      break;
    case "stats":
      botStore.updateStats(message.data as any);
      break;
    case "team_update":
      teamsStore.updateTeamFromWs(message.data as any);
      break;
    case "notification":
      console.log(`[${message.level}] ${message.message}`);
      break;
  }
}

const { isConnected, connect, disconnect } = useWebSocket(
  handleWebSocketMessage
);

onMounted(async () => {
  connect();
  await Promise.all([
    botStore.fetchState(),
    botStore.fetchStats(),
    teamsStore.fetchTeams(),
  ]);
});

onUnmounted(() => {
  disconnect();
});

const navItems = [
  { path: "/", name: "Dashboard", icon: LayoutDashboard },
  { path: "/teams", name: "Echipe", icon: Users },
  { path: "/history", name: "Istoric", icon: History },
  { path: "/settings", name: "Setări", icon: Settings },
];
</script>

<template>
  <div class="min-h-screen bg-gray-50">
    <nav class="bg-white border-b border-gray-200 fixed w-full z-10">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between h-16">
          <div class="flex items-center">
            <img src="/logo.png" alt="Logo" class="h-10 w-auto" />
          </div>

          <div class="flex items-center space-x-4">
            <RouterLink
              v-for="item in navItems"
              :key="item.path"
              :to="item.path"
              class="flex items-center px-3 py-2 rounded-lg text-sm font-medium transition-colors"
              :class="
                route.path === item.path
                  ? 'bg-primary-50 text-primary-600'
                  : 'text-gray-600 hover:bg-gray-100'
              "
            >
              <component :is="item.icon" class="h-5 w-5 mr-2" />
              {{ item.name }}
            </RouterLink>
          </div>

          <div class="flex items-center space-x-4">
            <div class="flex items-center">
              <span
                class="h-2 w-2 rounded-full mr-2"
                :class="isConnected ? 'bg-green-500' : 'bg-red-500'"
              ></span>
              <span class="text-sm text-gray-500">
                {{ isConnected ? "Conectat" : "Deconectat" }}
              </span>
            </div>

            <div
              class="badge"
              :class="{
                'badge-success': botStore.isRunning,
                'badge-danger': botStore.hasError,
                'badge-warning': botStore.isStopped,
              }"
            >
              {{ botStore.state.status.toUpperCase() }}
            </div>
          </div>
        </div>
      </div>
    </nav>

    <main class="pt-20 pb-8">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <RouterView />
      </div>
    </main>
  </div>
</template>
