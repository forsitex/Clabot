import { ref, type Ref } from "vue";
import type { WebSocketMessage } from "@/types";

export interface UseWebSocketReturn {
  isConnected: Ref<boolean>;
  lastMessage: Ref<WebSocketMessage | null>;
  connect: () => void;
  disconnect: () => void;
  send: (message: object) => void;
}

export function useWebSocket(
  onMessage?: (message: WebSocketMessage) => void
): UseWebSocketReturn {
  const isConnected = ref(false);
  const lastMessage = ref<WebSocketMessage | null>(null);
  let socket: WebSocket | null = null;
  let reconnectTimeout: ReturnType<typeof setTimeout> | null = null;

  function getWebSocketUrl(): string {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    return `${protocol}//${host}/ws`;
  }

  function connect(): void {
    if (socket?.readyState === WebSocket.OPEN) {
      return;
    }

    const url = getWebSocketUrl();
    socket = new WebSocket(url);

    socket.onopen = () => {
      isConnected.value = true;
      console.log("WebSocket conectat");
    };

    socket.onclose = () => {
      isConnected.value = false;
      console.log("WebSocket deconectat");

      reconnectTimeout = setTimeout(() => {
        console.log("Reconectare WebSocket...");
        connect();
      }, 3000);
    };

    socket.onerror = (error) => {
      console.error("Eroare WebSocket:", error);
    };

    socket.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data);
        lastMessage.value = message;

        if (message.type === "ping") {
          send({ type: "pong" });
          return;
        }

        if (onMessage) {
          onMessage(message);
        }
      } catch (error) {
        console.error("Eroare parsare mesaj WebSocket:", error);
      }
    };
  }

  function disconnect(): void {
    if (reconnectTimeout) {
      clearTimeout(reconnectTimeout);
      reconnectTimeout = null;
    }

    if (socket) {
      socket.close();
      socket = null;
    }

    isConnected.value = false;
  }

  function send(message: object): void {
    if (socket?.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify(message));
    }
  }

  return {
    isConnected,
    lastMessage,
    connect,
    disconnect,
    send,
  };
}
