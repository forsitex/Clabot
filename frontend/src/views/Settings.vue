<script setup lang="ts">
import { ref } from "vue";
import { Save, RefreshCw } from "lucide-vue-next";

const settings = ref({
  betfair_app_key: "",
  betfair_username: "",
  betfair_password: "",
  google_sheets_id: "",
  bot_run_hour: 13,
  bot_run_minute: 0,
  initial_stake: 100,
  max_progression_steps: 7,
});

const isSaving = ref(false);

async function handleSave(): Promise<void> {
  isSaving.value = true;
  try {
    console.log("Salvare setări:", settings.value);
    await new Promise((resolve) => setTimeout(resolve, 500));
    alert("Setările au fost salvate!");
  } finally {
    isSaving.value = false;
  }
}
</script>

<template>
  <div class="space-y-6">
    <h1 class="text-2xl font-bold text-gray-900">Setări</h1>

    <div class="card">
      <h2 class="text-lg font-semibold mb-4">Betfair API</h2>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label class="label">App Key</label>
          <input
            v-model="settings.betfair_app_key"
            type="text"
            class="input"
            placeholder="Betfair App Key"
          />
        </div>
        <div>
          <label class="label">Username</label>
          <input
            v-model="settings.betfair_username"
            type="text"
            class="input"
            placeholder="Betfair Username"
          />
        </div>
        <div class="md:col-span-2">
          <label class="label">Password</label>
          <input
            v-model="settings.betfair_password"
            type="password"
            class="input"
            placeholder="••••••••"
          />
        </div>
      </div>
    </div>

    <div class="card">
      <h2 class="text-lg font-semibold mb-4">Google Sheets</h2>
      <div>
        <label class="label">Spreadsheet ID</label>
        <input
          v-model="settings.google_sheets_id"
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
      <button class="btn btn-secondary flex items-center">
        <RefreshCw class="h-4 w-4 mr-2" />
        Resetează
      </button>
      <button
        @click="handleSave"
        :disabled="isSaving"
        class="btn btn-primary flex items-center"
      >
        <Save class="h-4 w-4 mr-2" />
        Salvează Setările
      </button>
    </div>
  </div>
</template>
