<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { CheckCircle, XCircle, Clock, AlertCircle } from "lucide-vue-next";
import * as api from "@/services/api";
import type { Bet } from "@/types";

const bets = ref<Bet[]>([]);
const isLoading = ref(false);
const statusFilter = ref<string>("");

onMounted(async () => {
  await fetchBets();
});

async function fetchBets(): Promise<void> {
  isLoading.value = true;
  try {
    const params: { status_filter?: string; limit?: number } = { limit: 100 };
    if (statusFilter.value) {
      params.status_filter = statusFilter.value;
    }
    bets.value = await api.getBets(params);
  } catch (error) {
    console.error("Eroare la încărcarea pariurilor:", error);
  } finally {
    isLoading.value = false;
  }
}

const filteredBets = computed(() => {
  if (!statusFilter.value) return bets.value;
  return bets.value.filter((b) => b.status === statusFilter.value);
});

function getStatusIcon(status: string) {
  switch (status) {
    case "won":
      return CheckCircle;
    case "lost":
      return XCircle;
    case "pending":
    case "placed":
    case "matched":
      return Clock;
    default:
      return AlertCircle;
  }
}

function getStatusColor(status: string): string {
  switch (status) {
    case "won":
      return "text-green-600 bg-green-50";
    case "lost":
      return "text-red-600 bg-red-50";
    case "pending":
    case "placed":
    case "matched":
      return "text-yellow-600 bg-yellow-50";
    default:
      return "text-gray-600 bg-gray-50";
  }
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("ro-RO", {
    style: "currency",
    currency: "RON",
  }).format(value);
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "-";
  return new Date(dateStr).toLocaleString("ro-RO");
}

async function handleSettle(bet: Bet, won: boolean): Promise<void> {
  try {
    await api.settleBet(bet.id, won);
    await fetchBets();
  } catch (error) {
    console.error("Eroare la finalizarea pariului:", error);
  }
}
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-bold text-gray-900">Istoric Pariuri</h1>

      <select v-model="statusFilter" @change="fetchBets" class="input w-48">
        <option value="">Toate</option>
        <option value="pending">În așteptare</option>
        <option value="placed">Plasate</option>
        <option value="matched">Matched</option>
        <option value="won">Câștigate</option>
        <option value="lost">Pierdute</option>
      </select>
    </div>

    <div class="card overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full">
          <thead class="bg-gray-50">
            <tr>
              <th
                class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase"
              >
                Status
              </th>
              <th
                class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase"
              >
                Echipă
              </th>
              <th
                class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase"
              >
                Eveniment
              </th>
              <th
                class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase"
              >
                Pronostic
              </th>
              <th
                class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase"
              >
                Cotă
              </th>
              <th
                class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase"
              >
                Miză
              </th>
              <th
                class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase"
              >
                Rezultat
              </th>
              <th
                class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase"
              >
                Data
              </th>
              <th
                class="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase"
              >
                Acțiuni
              </th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr
              v-for="bet in filteredBets"
              :key="bet.id"
              class="hover:bg-gray-50"
            >
              <td class="px-4 py-3">
                <span
                  class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium"
                  :class="getStatusColor(bet.status)"
                >
                  <component
                    :is="getStatusIcon(bet.status)"
                    class="h-3 w-3 mr-1"
                  />
                  {{ bet.status.toUpperCase() }}
                </span>
              </td>
              <td class="px-4 py-3 font-medium">{{ bet.team_name }}</td>
              <td class="px-4 py-3 text-sm text-gray-600">
                {{ bet.event_name }}
              </td>
              <td class="px-4 py-3">
                <span class="badge badge-primary">{{ bet.pronostic }}</span>
              </td>
              <td class="px-4 py-3 text-right font-medium">
                {{ bet.odds.toFixed(2) }}
              </td>
              <td class="px-4 py-3 text-right">
                {{ formatCurrency(bet.stake) }}
              </td>
              <td
                class="px-4 py-3 text-right font-medium"
                :class="
                  bet.result && bet.result > 0
                    ? 'text-green-600'
                    : bet.result && bet.result < 0
                    ? 'text-red-600'
                    : ''
                "
              >
                {{ bet.result !== null ? formatCurrency(bet.result) : "-" }}
              </td>
              <td class="px-4 py-3 text-sm text-gray-500">
                {{ formatDate(bet.created_at) }}
              </td>
              <td class="px-4 py-3 text-center">
                <div
                  v-if="bet.status === 'placed' || bet.status === 'matched'"
                  class="flex justify-center space-x-2"
                >
                  <button
                    @click="handleSettle(bet, true)"
                    class="p-1 text-green-600 hover:bg-green-50 rounded"
                    title="Marchează câștigat"
                  >
                    <CheckCircle class="h-4 w-4" />
                  </button>
                  <button
                    @click="handleSettle(bet, false)"
                    class="p-1 text-red-600 hover:bg-red-50 rounded"
                    title="Marchează pierdut"
                  >
                    <XCircle class="h-4 w-4" />
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>

        <div v-if="filteredBets.length === 0" class="text-center py-12">
          <p class="text-gray-500">Nu există pariuri.</p>
        </div>
      </div>
    </div>
  </div>
</template>
