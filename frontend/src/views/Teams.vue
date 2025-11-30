<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import {
  Plus,
  Pause,
  Play,
  RotateCcw,
  Trash2,
  ChevronDown,
  ChevronUp,
  Search,
  Loader2,
  DollarSign,
  Check,
  X,
} from "lucide-vue-next";
import { useTeamsStore } from "@/stores/teams";
import { searchTeamsBetfair, updateTeamInitialStake } from "@/services/api";
import type { Team, TeamCreate } from "@/types";

const teamsStore = useTeamsStore();

const showAddForm = ref(false);
const expandedTeam = ref<string | null>(null);

const newTeam = ref<TeamCreate>({
  name: "",
  sport: "football",
  league: "Auto",
  country: "",
});

const searchQuery = ref("");
const searchResults = ref<string[]>([]);
const isSearching = ref(false);
const showDropdown = ref(false);
let searchTimeout: ReturnType<typeof setTimeout> | null = null;

// Edit initial stake
const editingStakeTeamId = ref<string | null>(null);
const editStakeValue = ref<number>(5);
const isSavingStake = ref(false);

onMounted(() => {
  teamsStore.fetchTeams();
});

watch(searchQuery, (newVal) => {
  if (searchTimeout) clearTimeout(searchTimeout);

  if (newVal.length < 3) {
    searchResults.value = [];
    showDropdown.value = false;
    return;
  }

  isSearching.value = true;
  searchTimeout = setTimeout(async () => {
    try {
      searchResults.value = await searchTeamsBetfair(newVal);
      showDropdown.value = searchResults.value.length > 0;
    } catch (e) {
      searchResults.value = [];
    } finally {
      isSearching.value = false;
    }
  }, 300);
});

function selectTeam(teamName: string): void {
  newTeam.value.name = teamName;
  searchQuery.value = teamName;
  showDropdown.value = false;
}

function handleBlur(): void {
  setTimeout(() => {
    showDropdown.value = false;
  }, 200);
}

const sortedTeams = computed(() => {
  return [...teamsStore.teams].sort((a, b) => {
    if (a.status === "active" && b.status !== "active") return -1;
    if (a.status !== "active" && b.status === "active") return 1;
    return a.name.localeCompare(b.name);
  });
});

async function handleAddTeam(): Promise<void> {
  if (!newTeam.value.name || !newTeam.value.country) {
    return;
  }

  await teamsStore.createTeam(newTeam.value);

  newTeam.value = { name: "", sport: "football", league: "Auto", country: "" };
  searchQuery.value = "";
  showAddForm.value = false;
}

async function handlePause(team: Team): Promise<void> {
  await teamsStore.pauseTeam(team.id);
}

async function handleActivate(team: Team): Promise<void> {
  await teamsStore.activateTeam(team.id);
}

async function handleReset(team: Team): Promise<void> {
  if (confirm(`Resetezi progresia pentru ${team.name}?`)) {
    await teamsStore.resetProgression(team.id);
  }
}

async function handleDelete(team: Team): Promise<void> {
  if (confirm(`Ștergi echipa ${team.name}?`)) {
    await teamsStore.deleteTeam(team.id);
  }
}

function toggleExpand(teamId: string): void {
  expandedTeam.value = expandedTeam.value === teamId ? null : teamId;
}

function startEditStake(team: Team): void {
  editingStakeTeamId.value = team.id;
  editStakeValue.value = (team as any).initial_stake || 5;
}

function cancelEditStake(): void {
  editingStakeTeamId.value = null;
}

async function saveStake(team: Team): Promise<void> {
  if (editStakeValue.value <= 0) return;

  isSavingStake.value = true;
  try {
    await updateTeamInitialStake(team.id, editStakeValue.value);
    await teamsStore.fetchTeams();
    editingStakeTeamId.value = null;
  } catch (e) {
    console.error("Eroare la salvarea mizei:", e);
  } finally {
    isSavingStake.value = false;
  }
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
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Echipe</h1>
        <p class="text-gray-500">
          {{ teamsStore.activeTeams.length }} active din
          {{ teamsStore.totalTeams }}
        </p>
      </div>

      <button
        @click="showAddForm = !showAddForm"
        class="btn btn-primary flex items-center"
      >
        <Plus class="h-4 w-4 mr-2" />
        Adaugă Echipă
      </button>
    </div>

    <div v-if="showAddForm" class="card">
      <h2 class="text-lg font-semibold mb-4">Echipă Nouă</h2>
      <form
        @submit.prevent="handleAddTeam"
        class="grid grid-cols-1 md:grid-cols-2 gap-4"
      >
        <div class="relative">
          <label class="label">Nume Echipă (caută pe Betfair)</label>
          <div class="relative">
            <input
              v-model="searchQuery"
              type="text"
              class="input pr-10"
              placeholder="Scrie min. 3 caractere..."
              @focus="showDropdown = searchResults.length > 0"
              @blur="handleBlur"
            />
            <div class="absolute right-3 top-1/2 -translate-y-1/2">
              <Loader2
                v-if="isSearching"
                class="h-4 w-4 animate-spin text-gray-400"
              />
              <Search v-else class="h-4 w-4 text-gray-400" />
            </div>
          </div>

          <div
            v-if="showDropdown && searchResults.length > 0"
            class="absolute z-10 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-60 overflow-auto"
          >
            <button
              v-for="team in searchResults"
              :key="team"
              type="button"
              class="w-full px-4 py-2 text-left hover:bg-blue-50 focus:bg-blue-50 focus:outline-none"
              @mousedown.prevent="selectTeam(team)"
            >
              {{ team }}
            </button>
          </div>

          <p v-if="newTeam.name" class="mt-1 text-sm text-green-600">
            ✓ Selectat: {{ newTeam.name }}
          </p>
        </div>

        <div>
          <label class="label">Țară</label>
          <input
            v-model="newTeam.country"
            type="text"
            class="input"
            placeholder="ex: Spania"
            required
          />
        </div>

        <div class="md:col-span-2 flex justify-end space-x-3">
          <button
            type="button"
            @click="showAddForm = false"
            class="btn btn-secondary"
          >
            Anulează
          </button>
          <button
            type="submit"
            class="btn btn-primary"
            :disabled="teamsStore.isLoading"
          >
            Salvează
          </button>
        </div>
      </form>
    </div>

    <div class="space-y-3">
      <div v-for="team in sortedTeams" :key="team.id" class="card">
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-4">
            <div
              class="w-3 h-3 rounded-full"
              :class="
                team.status === 'active' ? 'bg-green-500' : 'bg-yellow-500'
              "
            ></div>

            <div>
              <h3 class="font-semibold text-gray-900">{{ team.name }}</h3>
              <p class="text-sm text-gray-500">
                {{ team.league }} • {{ team.country }}
              </p>
            </div>
          </div>

          <div class="flex items-center space-x-4">
            <div class="text-right">
              <p class="text-sm text-gray-500">Pierdere Cumulată</p>
              <p
                class="font-semibold"
                :class="
                  team.cumulative_loss > 0 ? 'text-red-600' : 'text-gray-900'
                "
              >
                {{ formatCurrency(team.cumulative_loss) }}
              </p>
            </div>

            <div class="text-right">
              <p class="text-sm text-gray-500">Pas Progresie</p>
              <p class="font-semibold">{{ team.progression_step }} / 7</p>
            </div>

            <div class="text-right">
              <p class="text-sm text-gray-500">Meciuri</p>
              <p class="font-semibold text-gray-900">
                <span class="text-green-600">{{ team.matches_won }}</span> /
                <span class="text-red-600">{{ team.matches_lost }}</span>
              </p>
            </div>

            <div class="text-right">
              <p class="text-sm text-gray-500">Profit Total</p>
              <p
                class="font-semibold"
                :class="
                  team.total_profit > 0
                    ? 'text-green-600'
                    : team.total_profit < 0
                    ? 'text-red-600'
                    : 'text-gray-900'
                "
              >
                {{ formatCurrency(team.total_profit) }}
              </p>
            </div>

            <div class="flex items-center space-x-2">
              <button
                v-if="team.status === 'active'"
                @click="handlePause(team)"
                class="p-2 text-yellow-600 hover:bg-yellow-50 rounded-lg"
                title="Pauză"
              >
                <Pause class="h-4 w-4" />
              </button>

              <button
                v-else
                @click="handleActivate(team)"
                class="p-2 text-green-600 hover:bg-green-50 rounded-lg"
                title="Activează"
              >
                <Play class="h-4 w-4" />
              </button>

              <button
                @click="handleReset(team)"
                class="p-2 text-blue-600 hover:bg-blue-50 rounded-lg"
                title="Reset Progresie"
              >
                <RotateCcw class="h-4 w-4" />
              </button>

              <button
                @click="handleDelete(team)"
                class="p-2 text-red-600 hover:bg-red-50 rounded-lg"
                title="Șterge"
              >
                <Trash2 class="h-4 w-4" />
              </button>

              <button
                @click="toggleExpand(team.id)"
                class="p-2 text-gray-400 hover:bg-gray-50 rounded-lg"
              >
                <component
                  :is="expandedTeam === team.id ? ChevronUp : ChevronDown"
                  class="h-4 w-4"
                />
              </button>
            </div>
          </div>
        </div>

        <div
          v-if="expandedTeam === team.id"
          class="mt-4 pt-4 border-t border-gray-100"
        >
          <div class="grid grid-cols-2 md:grid-cols-5 gap-4 text-sm">
            <div>
              <p class="text-gray-500">Sport</p>
              <p class="font-medium">
                {{ team.sport === "football" ? "Fotbal" : "Baschet" }}
              </p>
            </div>
            <div>
              <p class="text-gray-500">Ultima Miză</p>
              <p class="font-medium">{{ formatCurrency(team.last_stake) }}</p>
            </div>
            <div>
              <p class="text-gray-500">Betfair ID</p>
              <p class="font-medium">{{ team.betfair_id || "-" }}</p>
            </div>
            <div>
              <p class="text-gray-500">Creat</p>
              <p class="font-medium">
                {{ new Date(team.created_at).toLocaleDateString("ro-RO") }}
              </p>
            </div>
            <div>
              <p class="text-gray-500 flex items-center">
                <DollarSign class="h-3 w-3 mr-1" />
                Miză Inițială
              </p>
              <div
                v-if="editingStakeTeamId === team.id"
                class="flex items-center space-x-2 mt-1"
              >
                <input
                  v-model.number="editStakeValue"
                  type="number"
                  min="1"
                  step="1"
                  class="w-20 px-2 py-1 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
                <button
                  @click="saveStake(team)"
                  :disabled="isSavingStake"
                  class="p-1 text-green-600 hover:bg-green-50 rounded"
                  title="Salvează"
                >
                  <Check class="h-4 w-4" />
                </button>
                <button
                  @click="cancelEditStake"
                  class="p-1 text-red-600 hover:bg-red-50 rounded"
                  title="Anulează"
                >
                  <X class="h-4 w-4" />
                </button>
              </div>
              <div v-else class="flex items-center space-x-2">
                <p class="font-medium">
                  {{ (team as any).initial_stake || 5 }} RON
                </p>
                <button
                  @click="startEditStake(team)"
                  class="p-1 text-blue-600 hover:bg-blue-50 rounded"
                  title="Modifică"
                >
                  <DollarSign class="h-3 w-3" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-if="sortedTeams.length === 0" class="card text-center py-12">
        <p class="text-gray-500">Nu există echipe. Adaugă prima echipă!</p>
      </div>
    </div>
  </div>
</template>
