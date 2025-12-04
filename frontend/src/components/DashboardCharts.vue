<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { Doughnut, Bar, Line } from "vue-chartjs";
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend,
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  Filler,
} from "chart.js";
import { useBotStore } from "@/stores/bot";
import api from "@/services/api";

ChartJS.register(
  ArcElement,
  Tooltip,
  Legend,
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  Filler
);

const botStore = useBotStore();
const stats = computed(() => botStore.stats);

interface DailyData {
  date: string;
  profit: number;
  won: number;
  lost: number;
  pending: number;
  staked: number;
}

interface TeamProfit {
  name: string;
  profit: number;
  won: number;
  lost: number;
}

interface HistoryData {
  daily: DailyData[];
  team_profits: TeamProfit[];
}

const historyData = ref<HistoryData>({ daily: [], team_profits: [] });
const isLoading = ref(true);

async function fetchHistory(): Promise<void> {
  try {
    const response = await api.get("/stats/history?days=30");
    historyData.value = response.data;
  } catch (e) {
    console.error("Error fetching history:", e);
  } finally {
    isLoading.value = false;
  }
}

onMounted(() => {
  fetchHistory();
});

const winRateChartData = computed(() => ({
  labels: ["Câștigate", "Pierdute"],
  datasets: [
    {
      data: [stats.value.won_bets, stats.value.lost_bets],
      backgroundColor: ["#10B981", "#EF4444"],
      borderColor: ["#059669", "#DC2626"],
      borderWidth: 2,
    },
  ],
}));

const winRateChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: "bottom" as const,
    },
  },
  animation: {
    animateRotate: true,
    animateScale: true,
  },
};

const teamProfitChartData = computed(() => {
  const teams = historyData.value.team_profits.slice(0, 8);
  return {
    labels: teams.map((t) => t.name),
    datasets: [
      {
        label: "Profit (RON)",
        data: teams.map((t) => t.profit),
        backgroundColor: teams.map((t) =>
          t.profit >= 0 ? "rgba(16, 185, 129, 0.8)" : "rgba(239, 68, 68, 0.8)"
        ),
        borderColor: teams.map((t) => (t.profit >= 0 ? "#059669" : "#DC2626")),
        borderWidth: 1,
        borderRadius: 4,
      },
    ],
  };
});

const teamProfitChartOptions = {
  indexAxis: "y" as const,
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: false,
    },
  },
  scales: {
    x: {
      grid: {
        display: false,
      },
    },
    y: {
      grid: {
        display: false,
      },
    },
  },
  animation: {
    duration: 1000,
  },
};

const profitEvolutionChartData = computed(() => {
  const daily = historyData.value.daily;
  let cumulative = 0;
  const cumulativeData = daily.map((d) => {
    cumulative += d.profit;
    return cumulative;
  });

  return {
    labels: daily.map((d) => {
      const date = new Date(d.date);
      return date.toLocaleDateString("ro-RO", {
        day: "2-digit",
        month: "short",
      });
    }),
    datasets: [
      {
        label: "Profit Cumulat (RON)",
        data: cumulativeData,
        borderColor: "#3B82F6",
        backgroundColor: "rgba(59, 130, 246, 0.1)",
        fill: true,
        tension: 0.4,
        pointRadius: 3,
        pointBackgroundColor: "#3B82F6",
      },
    ],
  };
});

const profitEvolutionChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: false,
    },
  },
  scales: {
    x: {
      grid: {
        display: false,
      },
    },
    y: {
      grid: {
        color: "rgba(0, 0, 0, 0.05)",
      },
    },
  },
  animation: {
    duration: 1500,
  },
};

const dailyActivityChartData = computed(() => {
  const daily = historyData.value.daily;
  return {
    labels: daily.map((d) => {
      const date = new Date(d.date);
      return date.toLocaleDateString("ro-RO", {
        day: "2-digit",
        month: "short",
      });
    }),
    datasets: [
      {
        label: "Câștigate",
        data: daily.map((d) => d.won),
        backgroundColor: "rgba(16, 185, 129, 0.8)",
        borderColor: "#059669",
        borderWidth: 1,
        borderRadius: 4,
      },
      {
        label: "Pierdute",
        data: daily.map((d) => d.lost),
        backgroundColor: "rgba(239, 68, 68, 0.8)",
        borderColor: "#DC2626",
        borderWidth: 1,
        borderRadius: 4,
      },
    ],
  };
});

const dailyActivityChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: "bottom" as const,
    },
  },
  scales: {
    x: {
      stacked: true,
      grid: {
        display: false,
      },
    },
    y: {
      stacked: true,
      grid: {
        color: "rgba(0, 0, 0, 0.05)",
      },
      ticks: {
        stepSize: 1,
      },
    },
  },
  animation: {
    duration: 1200,
  },
};
</script>

<template>
  <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
    <div class="card">
      <h3 class="text-lg font-semibold mb-4">Win Rate</h3>
      <div class="h-64">
        <Doughnut
          v-if="stats.won_bets > 0 || stats.lost_bets > 0"
          :data="winRateChartData"
          :options="winRateChartOptions"
        />
        <div
          v-else
          class="flex items-center justify-center h-full text-gray-400"
        >
          Nu există date
        </div>
      </div>
    </div>

    <div class="card">
      <h3 class="text-lg font-semibold mb-4">Profit per Echipă</h3>
      <div class="h-64">
        <Bar
          v-if="historyData.team_profits.length > 0"
          :data="teamProfitChartData"
          :options="teamProfitChartOptions"
        />
        <div
          v-else-if="isLoading"
          class="flex items-center justify-center h-full text-gray-400"
        >
          Se încarcă...
        </div>
        <div
          v-else
          class="flex items-center justify-center h-full text-gray-400"
        >
          Nu există date
        </div>
      </div>
    </div>

    <div class="card">
      <h3 class="text-lg font-semibold mb-4">Evoluție Profit</h3>
      <div class="h-64">
        <Line
          v-if="historyData.daily.length > 0"
          :data="profitEvolutionChartData"
          :options="profitEvolutionChartOptions"
        />
        <div
          v-else-if="isLoading"
          class="flex items-center justify-center h-full text-gray-400"
        >
          Se încarcă...
        </div>
        <div
          v-else
          class="flex items-center justify-center h-full text-gray-400"
        >
          Nu există date
        </div>
      </div>
    </div>

    <div class="card">
      <h3 class="text-lg font-semibold mb-4">Activitate Zilnică</h3>
      <div class="h-64">
        <Bar
          v-if="historyData.daily.length > 0"
          :data="dailyActivityChartData"
          :options="dailyActivityChartOptions"
        />
        <div
          v-else-if="isLoading"
          class="flex items-center justify-center h-full text-gray-400"
        >
          Se încarcă...
        </div>
        <div
          v-else
          class="flex items-center justify-center h-full text-gray-400"
        >
          Nu există date
        </div>
      </div>
    </div>
  </div>
</template>
