<script setup lang="ts">
import { ref, onMounted } from "vue";
import {
  Save,
  RefreshCw,
  CheckCircle,
  XCircle,
  Loader2,
} from "lucide-vue-next";
import * as api from "@/services/api";
import type { AppSettings, SettingsUpdate } from "@/services/api";

const settings = ref<AppSettings>({
  betfair_app_key: "",
  betfair_username: "",
  betfair_password: "",
  betfair_cert_file: null,
  betfair_key_file: null,
  google_sheets_spreadsheet_id: "",
  google_credentials_file: null,
  bot_run_hour: 13,
  bot_run_minute: 0,
  initial_stake: 100,
  max_progression_steps: 7,
  betfair_connected: false,
  google_sheets_connected: false,
});

const isLoading = ref(false);
const isSaving = ref(false);
const isTesting = ref({ betfair: false, sheets: false });
const message = ref<{ type: "success" | "error"; text: string } | null>(null);

onMounted(async () => {
  await loadSettings();
  await checkBetfairStatus();
});

async function loadSettings(): Promise<void> {
  isLoading.value = true;
  try {
    settings.value = await api.getSettings();
  } catch (error) {
    showMessage("error", "Eroare la încărcarea setărilor");
  } finally {
    isLoading.value = false;
  }
}

async function handleSave(): Promise<void> {
  isSaving.value = true;
  message.value = null;
  try {
    const updates: SettingsUpdate = {
      betfair_app_key: settings.value.betfair_app_key,
      betfair_username: settings.value.betfair_username,
      betfair_password: settings.value.betfair_password,
      google_sheets_spreadsheet_id: settings.value.google_sheets_spreadsheet_id,
      bot_run_hour: settings.value.bot_run_hour,
      bot_run_minute: settings.value.bot_run_minute,
      initial_stake: settings.value.initial_stake,
      max_progression_steps: settings.value.max_progression_steps,
    };
    settings.value = await api.updateSettings(updates);
    // Re-check Betfair status after save
    await checkBetfairStatus();
    showMessage("success", "Setările au fost salvate!");
  } catch (error) {
    showMessage("error", "Eroare la salvarea setărilor");
  } finally {
    isSaving.value = false;
  }
}

async function testBetfair(): Promise<void> {
  isTesting.value.betfair = true;
  try {
    const result = await api.testBetfairConnection();
    if (result.success) {
      settings.value.betfair_connected = true;
      showMessage("success", result.message);
    } else {
      settings.value.betfair_connected = false;
      showMessage("error", result.message);
    }
  } catch (error) {
    showMessage("error", "Eroare la testarea conexiunii Betfair");
  } finally {
    isTesting.value.betfair = false;
  }
}

async function checkBetfairStatus(): Promise<void> {
  try {
    const status = await api.getBetfairStatus();
    settings.value.betfair_connected = status.connected;
  } catch (error) {
    console.error("Error checking Betfair status:", error);
  }
}

async function testGoogleSheets(): Promise<void> {
  isTesting.value.sheets = true;
  try {
    await handleSave();
    const result = await api.testGoogleSheetsConnection();
    if (result.success) {
      settings.value.google_sheets_connected = true;
      showMessage("success", result.message);
    } else {
      settings.value.google_sheets_connected = false;
      showMessage("error", result.message);
    }
  } catch (error) {
    showMessage("error", "Eroare la testarea conexiunii Google Sheets");
  } finally {
    isTesting.value.sheets = false;
  }
}

function showMessage(type: "success" | "error", text: string): void {
  message.value = { type, text };
  setTimeout(() => {
    message.value = null;
  }, 5000);
}

async function handleReset(): Promise<void> {
  await loadSettings();
  showMessage("success", "Setările au fost resetate");
}
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-bold text-gray-900">Setări</h1>
      <div v-if="isLoading" class="flex items-center text-gray-500">
        <Loader2 class="h-5 w-5 animate-spin mr-2" />
        Se încarcă...
      </div>
    </div>

    <div
      v-if="message"
      class="p-4 rounded-lg"
      :class="
        message.type === 'success'
          ? 'bg-green-50 text-green-700'
          : 'bg-red-50 text-red-700'
      "
    >
      <div class="flex items-center">
        <CheckCircle v-if="message.type === 'success'" class="h-5 w-5 mr-2" />
        <XCircle v-else class="h-5 w-5 mr-2" />
        {{ message.text }}
      </div>
    </div>

    <div class="card">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-lg font-semibold">Betfair API</h2>
        <div class="flex items-center space-x-2">
          <span
            class="badge"
            :class="
              settings.betfair_connected ? 'badge-success' : 'badge-danger'
            "
          >
            {{ settings.betfair_connected ? "Conectat" : "Neconectat" }}
          </span>
          <button
            @click="testBetfair"
            :disabled="isTesting.betfair"
            class="btn btn-secondary text-sm py-1 px-3"
          >
            <Loader2
              v-if="isTesting.betfair"
              class="h-4 w-4 animate-spin mr-1"
            />
            Test Conexiune
          </button>
        </div>
      </div>
      <div class="text-sm text-gray-600">
        <p>Credențialele Betfair sunt configurate automat din server.</p>
        <p class="mt-2">
          Click pe "Test Conexiune" pentru a verifica conexiunea la Betfair API.
        </p>
      </div>
    </div>

    <div class="card">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-lg font-semibold">Google Sheets</h2>
        <div class="flex items-center space-x-2">
          <span
            class="badge"
            :class="
              settings.google_sheets_connected
                ? 'badge-success'
                : 'badge-danger'
            "
          >
            {{ settings.google_sheets_connected ? "Conectat" : "Neconectat" }}
          </span>
          <button
            @click="testGoogleSheets"
            :disabled="isTesting.sheets"
            class="btn btn-secondary text-sm py-1 px-3"
          >
            <Loader2
              v-if="isTesting.sheets"
              class="h-4 w-4 animate-spin mr-1"
            />
            Testează
          </button>
        </div>
      </div>
      <div>
        <label class="label">Spreadsheet ID</label>
        <input
          v-model="settings.google_sheets_spreadsheet_id"
          type="text"
          class="input"
          placeholder="ID-ul spreadsheet-ului din URL"
        />
        <p class="text-xs text-gray-500 mt-1">
          Găsești ID-ul în URL:
          docs.google.com/spreadsheets/d/<strong>[ID]</strong>/edit
        </p>
      </div>
    </div>

    <div class="card">
      <h2 class="text-lg font-semibold mb-4">Configurare Bot</h2>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label class="label">Ora Execuție (HH:MM)</label>
          <div class="flex space-x-2">
            <input
              v-model.number="settings.bot_run_hour"
              type="number"
              min="0"
              max="23"
              class="input w-20"
            />
            <span class="self-center">:</span>
            <input
              v-model.number="settings.bot_run_minute"
              type="number"
              min="0"
              max="59"
              class="input w-20"
            />
          </div>
        </div>

        <div>
          <label class="label">Miză Inițială (RON)</label>
          <input
            v-model.number="settings.initial_stake"
            type="number"
            min="1"
            class="input"
          />
        </div>

        <div>
          <label class="label">Max Pași Progresie (Stop Loss)</label>
          <input
            v-model.number="settings.max_progression_steps"
            type="number"
            min="1"
            max="20"
            class="input"
          />
          <p class="text-xs text-gray-500 mt-1">
            După acest număr de pierderi consecutive, botul oprește pariurile pe
            echipă
          </p>
        </div>
      </div>
    </div>

    <div class="flex justify-end space-x-3">
      <button @click="handleReset" class="btn btn-secondary flex items-center">
        <RefreshCw class="h-4 w-4 mr-2" />
        Resetează
      </button>
      <button
        @click="handleSave"
        :disabled="isSaving"
        class="btn btn-primary flex items-center"
      >
        <Loader2 v-if="isSaving" class="h-4 w-4 animate-spin mr-2" />
        <Save v-else class="h-4 w-4 mr-2" />
        Salvează Setările
      </button>
    </div>
  </div>
</template>
