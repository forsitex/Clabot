<script setup lang="ts">
import { computed } from "vue";
import {
  Play,
  Square,
  TrendingUp,
  TrendingDown,
  Users,
  Target,
  DollarSign,
  Percent,
} from "lucide-vue-next";
import { useBotStore } from "@/stores/bot";
import DashboardCharts from "@/components/DashboardCharts.vue";

const botStore = useBotStore();

const stats = computed(() => botStore.stats);
const state = computed(() => botStore.state);

async function handleRunNow(): Promise<void> {
  await botStore.start();
  await botStore.runNow();
}

async function handleStop(): Promise<void> {
  await botStore.stop();
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "-";
  return new Date(dateStr).toLocaleString("ro-RO");
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("ro-RO", {
    style: "currency",
    currency: "RON",
  }).format(value);
}
</script>

<template>
  <div class="space-y-6">
    <div
      class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3"
    >
      <h1 class="text-xl sm:text-2xl font-bold text-gray-900">Dashboard</h1>

      <div class="flex items-center space-x-2 sm:space-x-3">
        <button
          v-if="!botStore.isRunning"
          @click="handleRunNow"
          :disabled="botStore.isLoading"
          class="btn btn-success flex items-center text-xs sm:text-sm py-2 px-3 sm:py-2.5 sm:px-4"
        >
          <Play class="h-3 w-3 sm:h-4 sm:w-4 mr-1 sm:mr-2" />
          Start
        </button>

        <button
          v-if="botStore.isRunning"
          @click="handleStop"
          :disabled="botStore.isLoading"
          class="btn btn-danger flex items-center text-xs sm:text-sm py-2 px-3 sm:py-2.5 sm:px-4"
        >
          <Square class="h-3 w-3 sm:h-4 sm:w-4 mr-1 sm:mr-2" />
          Stop
        </button>
      </div>
    </div>

    <div class="card">
      <h2 class="text-lg font-semibold mb-4">Stare Bot</h2>
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div>
          <p class="text-sm text-gray-500">Status</p>
          <p
            class="text-lg font-medium"
            :class="{
              'text-green-600': botStore.isRunning,
              'text-red-600': botStore.hasError,
              'text-yellow-600': botStore.isStopped,
            }"
          >
            {{ state.status.toUpperCase() }}
          </p>
        </div>
        <div>
          <p class="text-sm text-gray-500">Ultima Execuție</p>
          <p class="text-lg font-medium">{{ formatDate(state.last_run) }}</p>
        </div>
        <div>
          <p class="text-sm text-gray-500">Pariuri Azi</p>
          <p class="text-lg font-medium">{{ state.bets_placed_today }}</p>
        </div>
        <div>
          <p class="text-sm text-gray-500">Miză Totală Azi</p>
          <p class="text-lg font-medium">
            {{ formatCurrency(state.total_stake_today) }}
          </p>
        </div>
      </div>

      <div v-if="state.last_error" class="mt-4 p-3 bg-red-50 rounded-lg">
        <p class="text-sm text-red-600">{{ state.last_error }}</p>
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      <div class="card">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-gray-500">Echipe Active</p>
            <p class="text-2xl font-bold">
              {{ stats.active_teams }} / {{ stats.total_teams }}
            </p>
          </div>
          <div class="p-3 bg-primary-50 rounded-lg">
            <Users class="h-6 w-6 text-primary-600" />
          </div>
        </div>
      </div>

      <div class="card">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-gray-500">Profit Total</p>
            <p
              class="text-2xl font-bold"
              :class="
                stats.total_profit >= 0 ? 'text-green-600' : 'text-red-600'
              "
            >
              {{ formatCurrency(stats.total_profit) }}
            </p>
          </div>
          <div
            class="p-3 rounded-lg"
            :class="stats.total_profit >= 0 ? 'bg-green-50' : 'bg-red-50'"
          >
            <component
              :is="stats.total_profit >= 0 ? TrendingUp : TrendingDown"
              class="h-6 w-6"
              :class="
                stats.total_profit >= 0 ? 'text-green-600' : 'text-red-600'
              "
            />
          </div>
        </div>
      </div>

      <div class="card">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-gray-500">Win Rate</p>
            <p class="text-2xl font-bold">{{ stats.win_rate.toFixed(1) }}%</p>
          </div>
          <div class="p-3 bg-blue-50 rounded-lg">
            <Percent class="h-6 w-6 text-blue-600" />
          </div>
        </div>
      </div>

      <div class="card">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-gray-500">Total Pariuri</p>
            <p class="text-2xl font-bold">{{ stats.total_bets }}</p>
            <p class="text-xs text-gray-400">
              {{ stats.won_bets }}W / {{ stats.lost_bets }}L /
              {{ stats.pending_bets }}P
            </p>
          </div>
          <div class="p-3 bg-purple-50 rounded-lg">
            <Target class="h-6 w-6 text-purple-600" />
          </div>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-lg font-semibold">Sumar Financiar</h2>
      </div>
      <div class="grid grid-cols-3 gap-6">
        <div class="text-center p-4 bg-gray-50 rounded-lg">
          <DollarSign class="h-8 w-8 mx-auto text-gray-400 mb-2" />
          <p class="text-sm text-gray-500">Total Mizat</p>
          <p class="text-xl font-bold">
            {{ formatCurrency(stats.total_staked) }}
          </p>
        </div>
        <div class="text-center p-4 bg-green-50 rounded-lg">
          <TrendingUp class="h-8 w-8 mx-auto text-green-500 mb-2" />
          <p class="text-sm text-gray-500">Câștiguri</p>
          <p class="text-xl font-bold text-green-600">
            {{ stats.won_bets }} pariuri
          </p>
        </div>
        <div class="text-center p-4 bg-red-50 rounded-lg">
          <TrendingDown class="h-8 w-8 mx-auto text-red-500 mb-2" />
          <p class="text-sm text-gray-500">Pierderi</p>
          <p class="text-xl font-bold text-red-600">
            {{ stats.lost_bets }} pariuri
          </p>
        </div>
      </div>
    </div>

    <DashboardCharts />
  </div>
</template>
