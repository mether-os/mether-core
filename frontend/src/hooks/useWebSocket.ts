import { useEffect, useRef, useCallback } from "react";
import { useMetherStore } from "@/stores/metherStore";
import type { ConnectionStatus } from "@/stores/metherStore";

/* ═══════════════════════════════════════════════════════════════
   METHER OS — WebSocket Connection Manager

   • Auto-connects to ws://localhost:8000/ws on mount
   • Exponential backoff reconnect (1s → 2s → 4s → 8s max)
   • Parses incoming JSON: { type, data }
   • Routes messages to Zustand store
   • Graceful fallback to demo mode when backend is offline
   ═══════════════════════════════════════════════════════════════ */

const WS_URL = "ws://localhost:8000/ws";
const BASE_DELAY = 1000;
const MAX_DELAY = 8000;

export interface WebSocketHook {
  isConnected: boolean;
  send: (message: string) => void;
  lastMessage: string | null;
  connectionStatus: ConnectionStatus;
}

export function useWebSocket(): WebSocketHook {
  const wsRef = useRef<WebSocket | null>(null);
  const retryCount = useRef(0);
  const retryTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastMessageRef = useRef<string | null>(null);
  const mountedRef = useRef(true);

  const {
    connectionStatus,
    setConnectionStatus,
    addLog,
    setOrbState,
    incrementStat,
    setActiveTool,
  } = useMetherStore();

  const isConnected = connectionStatus === "connected";

  /* ── Connect ── */
  const connect = useCallback(() => {
    if (!mountedRef.current) return;

    // Clean up existing socket
    if (wsRef.current) {
      wsRef.current.onopen = null;
      wsRef.current.onclose = null;
      wsRef.current.onmessage = null;
      wsRef.current.onerror = null;
      if (wsRef.current.readyState < 2) wsRef.current.close();
    }

    setConnectionStatus("connecting");
    addLog("WS", `Connecting to ${WS_URL}...`);

    try {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!mountedRef.current) return;
        retryCount.current = 0;
        setConnectionStatus("connected");
        addLog("WS", "Connection established");
        addLog("SYSTEM", "Backend link active — live mode");
      };

      ws.onclose = (e) => {
        if (!mountedRef.current) return;
        setConnectionStatus("disconnected");

        if (e.code !== 1000) {
          // Abnormal close → retry
          scheduleReconnect();
        }
      };

      ws.onerror = () => {
        if (!mountedRef.current) return;
        setConnectionStatus("error");
        addLog("WS", "Connection failed — running in demo mode");
        ws.close();
      };

      ws.onmessage = (event) => {
        if (!mountedRef.current) return;
        lastMessageRef.current = event.data;

        try {
          const msg = JSON.parse(event.data) as { type: string; data?: unknown };
          handleMessage(msg);
        } catch {
          // Non-JSON message — treat as raw text
          addLog("WS", String(event.data));
        }
      };
    } catch {
      setConnectionStatus("error");
      addLog("WS", "Failed to create WebSocket — running in demo mode");
      scheduleReconnect();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /* ── Handle parsed messages ── */
  const handleMessage = useCallback(
    (msg: { type: string; data?: unknown }) => {
      switch (msg.type) {
        case "orb_state":
          if (typeof msg.data === "string") {
            setOrbState(msg.data as "idle" | "listening" | "processing" | "speaking");
          }
          break;

        case "log":
          if (msg.data && typeof msg.data === "object" && "module" in msg.data && "message" in msg.data) {
            const d = msg.data as { module: string; message: string };
            addLog(d.module, d.message);
          }
          break;

        case "tool_active":
          if (typeof msg.data === "string") {
            setActiveTool(msg.data);
            addLog("TOOL", `Active: ${msg.data}`);
          }
          break;

        case "stats":
          if (msg.data && typeof msg.data === "object") {
            const d = msg.data as Record<string, number>;
            for (const [key, val] of Object.entries(d)) {
              if (["commands", "toolsUsed", "memoryHits", "tokens"].includes(key)) {
                incrementStat(key as "commands" | "toolsUsed" | "memoryHits" | "tokens", val);
              }
            }
          }
          break;

        case "pong":
          // Heartbeat response — no-op
          break;

        default:
          addLog("WS", `Unknown message type: ${msg.type}`);
      }
    },
    [addLog, setOrbState, setActiveTool, incrementStat]
  );

  /* ── Reconnect with exponential backoff ── */
  const scheduleReconnect = useCallback(() => {
    if (!mountedRef.current) return;

    const delay = Math.min(BASE_DELAY * Math.pow(2, retryCount.current), MAX_DELAY);
    retryCount.current++;

    addLog("WS", `Reconnecting in ${delay / 1000}s (attempt ${retryCount.current})`);

    retryTimer.current = setTimeout(() => {
      if (mountedRef.current) connect();
    }, delay);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [connect]);

  /* ── Send ── */
  const send = useCallback(
    (message: string) => {
      const ws = wsRef.current;
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "command", data: message }));
      } else {
        // Offline — log locally
        addLog("CMD", message);
        addLog("SYSTEM", "Command queued — backend offline");
      }
    },
    [addLog]
  );

  /* ── Lifecycle ── */
  useEffect(() => {
    mountedRef.current = true;
    connect();

    return () => {
      mountedRef.current = false;
      if (retryTimer.current) clearTimeout(retryTimer.current);
      if (wsRef.current) {
        wsRef.current.onclose = null; // prevent reconnect on unmount
        wsRef.current.close(1000);
      }
    };
  }, [connect]);

  return {
    isConnected,
    send,
    lastMessage: lastMessageRef.current,
    connectionStatus,
  };
}
