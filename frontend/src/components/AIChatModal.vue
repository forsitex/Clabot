<script setup lang="ts">
import { ref, nextTick, watch } from "vue";
import { X, Send, Trash2, Loader2, Bot, User } from "lucide-vue-next";
import axios from "axios";

const props = defineProps<{
  isOpen: boolean;
}>();

const emit = defineEmits<{
  close: [];
}>();

interface Message {
  role: "user" | "assistant";
  content: string;
}

const messages = ref<Message[]>([]);
const inputMessage = ref("");
const isLoading = ref(false);
const chatContainer = ref<HTMLElement | null>(null);

watch(
  () => props.isOpen,
  (open) => {
    if (open && messages.value.length === 0) {
      messages.value.push({
        role: "assistant",
        content:
          "Salut! Sunt asistentul tău pentru analiză meciuri și pronosticuri. Întreabă-mă despre orice meci, cotă sau strategie de pariere.",
      });
    }
  }
);

async function sendMessage(): Promise<void> {
  if (!inputMessage.value.trim() || isLoading.value) return;

  const userMessage = inputMessage.value.trim();
  inputMessage.value = "";

  messages.value.push({
    role: "user",
    content: userMessage,
  });

  await scrollToBottom();
  isLoading.value = true;

  try {
    const token = localStorage.getItem("auth_token");
    const response = await axios.post(
      "/api/ai/chat",
      { message: userMessage },
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    );

    messages.value.push({
      role: "assistant",
      content: response.data.response,
    });
  } catch (error) {
    messages.value.push({
      role: "assistant",
      content: "Eroare la procesarea mesajului. Încearcă din nou.",
    });
  } finally {
    isLoading.value = false;
    await scrollToBottom();
  }
}

async function clearChat(): Promise<void> {
  try {
    const token = localStorage.getItem("auth_token");
    await axios.post(
      "/api/ai/clear",
      {},
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    );
    messages.value = [
      {
        role: "assistant",
        content: "Conversație ștearsă. Cu ce te pot ajuta?",
      },
    ];
  } catch (error) {
    console.error("Eroare la ștergerea conversației:", error);
  }
}

async function scrollToBottom(): Promise<void> {
  await nextTick();
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight;
  }
}

function handleKeydown(event: KeyboardEvent): void {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    sendMessage();
  }
}
</script>

<template>
  <Teleport to="body">
    <div
      v-if="isOpen"
      class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50"
      @click.self="emit('close')"
    >
      <div
        class="bg-white rounded-2xl shadow-2xl w-full max-w-lg h-[600px] max-h-[90vh] flex flex-col overflow-hidden"
      >
        <div
          class="flex items-center justify-between px-4 py-3 border-b bg-gradient-to-r from-primary-600 to-primary-700"
        >
          <div class="flex items-center space-x-2">
            <Bot class="h-6 w-6 text-white" />
            <h2 class="text-lg font-semibold text-white">
              Asistent Pronosticuri
            </h2>
          </div>
          <div class="flex items-center space-x-2">
            <button
              @click="clearChat"
              class="p-2 text-white/80 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
              title="Șterge conversația"
            >
              <Trash2 class="h-5 w-5" />
            </button>
            <button
              @click="emit('close')"
              class="p-2 text-white/80 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
            >
              <X class="h-5 w-5" />
            </button>
          </div>
        </div>

        <div
          ref="chatContainer"
          class="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50"
        >
          <div
            v-for="(message, index) in messages"
            :key="index"
            class="flex"
            :class="message.role === 'user' ? 'justify-end' : 'justify-start'"
          >
            <div
              class="flex items-start space-x-2 max-w-[85%]"
              :class="
                message.role === 'user'
                  ? 'flex-row-reverse space-x-reverse'
                  : ''
              "
            >
              <div
                class="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center"
                :class="
                  message.role === 'user'
                    ? 'bg-primary-600 text-white'
                    : 'bg-gray-200 text-gray-600'
                "
              >
                <User v-if="message.role === 'user'" class="h-4 w-4" />
                <Bot v-else class="h-4 w-4" />
              </div>
              <div
                class="px-4 py-2 rounded-2xl"
                :class="
                  message.role === 'user'
                    ? 'bg-primary-600 text-white rounded-tr-sm'
                    : 'bg-white text-gray-800 shadow-sm rounded-tl-sm'
                "
              >
                <p class="text-sm whitespace-pre-wrap">{{ message.content }}</p>
              </div>
            </div>
          </div>

          <div v-if="isLoading" class="flex justify-start">
            <div class="flex items-start space-x-2">
              <div
                class="flex-shrink-0 w-8 h-8 rounded-full bg-gray-200 text-gray-600 flex items-center justify-center"
              >
                <Bot class="h-4 w-4" />
              </div>
              <div
                class="px-4 py-3 bg-white rounded-2xl rounded-tl-sm shadow-sm"
              >
                <Loader2 class="h-5 w-5 animate-spin text-primary-600" />
              </div>
            </div>
          </div>
        </div>

        <div class="p-4 border-t bg-white">
          <div class="flex items-center space-x-2">
            <input
              v-model="inputMessage"
              @keydown="handleKeydown"
              type="text"
              placeholder="Întreabă despre meciuri, cote, pronosticuri..."
              class="flex-1 px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-sm"
              :disabled="isLoading"
            />
            <button
              @click="sendMessage"
              :disabled="!inputMessage.trim() || isLoading"
              class="p-2.5 bg-primary-600 text-white rounded-xl hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <Send class="h-5 w-5" />
            </button>
          </div>
          <p class="text-xs text-gray-400 mt-2 text-center">
            Analizele sunt informative. Pariurile implică risc.
          </p>
        </div>
      </div>
    </div>
  </Teleport>
</template>
