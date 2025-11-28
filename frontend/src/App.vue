<script setup lang="ts">
import { onMounted, onUnmounted, computed } from "vue";
import { RouterView, RouterLink, useRoute, useRouter } from "vue-router";
import {
  LayoutDashboard,
  Users,
  History,
  Settings,
  LogOut,
} from "lucide-vue-next";
import { useBotStore } from "@/stores/bot";
import { useTeamsStore } from "@/stores/teams";
import { useWebSocket } from "@/services/websocket";
import type { WebSocketMessage } from "@/types";

const route = useRoute();
const router = useRouter();
const botStore = useBotStore();
const teamsStore = useTeamsStore();

const isLoginPage = computed(() => route.path === "/login");

function handleLogout(): void {
  localStorage.removeItem("auth_token");
  router.push("/login");
}

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
  <div v-if="isLoginPage">
    <RouterView />
  </div>
  <div v-else class="min-h-screen bg-gray-50">
    <nav class="bg-white border-b border-gray-200 fixed w-full z-10">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div
          class="flex flex-col lg:flex-row lg:justify-between py-2 lg:py-0 lg:h-16"
        >
          <div
            class="flex items-center justify-center lg:justify-start py-2 lg:py-0"
          >
            <img src="/logo.png" alt="Logo" class="h-8 lg:h-10 w-auto" />
            <span
              class="ml-3 text-gray-700 font-medium text-sm lg:text-base hidden sm:inline"
            >
              Strategie automatizată 24/7
            </span>
          </div>

          <div
            class="flex items-center justify-center space-x-1 sm:space-x-2 lg:space-x-4 overflow-x-auto py-2 lg:py-0"
          >
            <RouterLink
              v-for="item in navItems"
              :key="item.path"
              :to="item.path"
              class="flex items-center px-2 sm:px-3 py-2 rounded-lg text-xs sm:text-sm font-medium transition-colors whitespace-nowrap"
              :class="
                route.path === item.path
                  ? 'bg-primary-50 text-primary-600'
                  : 'text-gray-600 hover:bg-gray-100'
              "
            >
              <component
                :is="item.icon"
                class="h-4 w-4 sm:h-5 sm:w-5 mr-1 sm:mr-2"
              />
              <span class="hidden sm:inline">{{ item.name }}</span>
            </RouterLink>

            <div class="flex items-center ml-2 pl-2 border-l border-gray-200">
              <span
                class="h-2 w-2 rounded-full mr-1"
                :class="isConnected ? 'bg-green-500' : 'bg-red-500'"
              ></span>
              <span class="text-xs text-gray-500 hidden sm:inline">
                {{ isConnected ? "Conectat" : "Deconectat" }}
              </span>
            </div>

            <div
              class="badge text-xs"
              :class="{
                'badge-success': botStore.isRunning,
                'badge-danger': botStore.hasError,
                'badge-warning': botStore.isStopped,
              }"
            >
              {{ botStore.state.status.toUpperCase() }}
            </div>

            <button
              @click="handleLogout"
              class="flex items-center px-2 sm:px-3 py-2 rounded-lg text-xs sm:text-sm font-medium text-red-600 hover:bg-red-50 transition-colors"
              title="Deconectare"
            >
              <LogOut class="h-4 w-4 sm:h-5 sm:w-5" />
              <span class="hidden sm:inline ml-1">Ieșire</span>
            </button>
          </div>
        </div>
      </div>
    </nav>

    <main class="pt-28 lg:pt-20 pb-8">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <RouterView />
      </div>
    </main>
  </div>
</template>
