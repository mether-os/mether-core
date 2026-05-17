import React, { useEffect, useRef, useCallback } from "react";
import { useMetherStore } from "@/stores/metherStore";
import type { ConnectionStatus } from "@/stores/metherStore";

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
  const [lastMessage, setLastMessage] = React.useState<string | null>(null);
  const mountedRef = useRef(true);

  const {
    connectionStatus,
    setConnectionStatus,
    addLog,
    setOrbState,
    incrementStat,
    setActiveTool,
    setActiveResponse,
    addSummary,
    addPing,
    removePing,
    setSocketSend,
    setVoiceStatus,
    setLastVoiceHeard,
    setVoiceLatency,
    setWakeWordTime,
    wakeWordTime,
  } = useMetherStore();

  const isConnected = connectionStatus === "connected";

  const send = useCallback(
    (message: string) => {
      const ws = wsRef.current;
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "message", text: message }));
      } else {
        addLog("CMD", message);
        addLog("SYSTEM", "Command queued — backend offline");
      }
    },
    [addLog]
  );

  useEffect(() => {
    mountedRef.current = true;

    const handleMessage = (msg: Record<string, unknown>) => {
      switch (msg.type) {
        case "orb_state":
          if (typeof msg.state === "string") {
            setOrbState(msg.state as "idle" | "listening" | "processing" | "speaking");
            if (msg.state === "listening") {
              setWakeWordTime(Date.now());
              setVoiceLatency(null);
            } else if (msg.state === "speaking" && wakeWordTime) {
              setVoiceLatency(Date.now() - wakeWordTime);
            }
          }
          break;
        case "log":
          if (msg.module && msg.message) {
            addLog(msg.module, msg.message);
            if (msg.module === "VOICE" && msg.message.startsWith("Heard: ")) {
              setLastVoiceHeard(msg.message.replace("Heard: ", ""));
            }
          }
          break;
        case "response":
          if (typeof msg.text === "string") {
            setActiveResponse(msg.source === "voice" ? `[VOICE] ${msg.text}` : msg.text);
          }
          break;
        case "voice_status":
          if (typeof msg.status === "string" && (msg.status === "online" || msg.status === "offline")) {
            setVoiceStatus(msg.status);
          }
          break;
        case "agent.thinking":
          break;
        case "tool.start":
          if (msg.data && msg.data.tool) {
            setActiveTool(msg.data.tool);
            addLog("TOOL", `Active: ${msg.data.tool}`);
          }
          break;
        case "tool.done":
          if (msg.data && msg.data.tool) {
            addLog("TOOL", `Done: ${msg.data.tool}`);
            setActiveTool("STANDBY");
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
          break;
        case "whatsapp_auto_reply":
          if (msg.to && msg.message) {
            addLog("WA_AUTO", `↩ ${msg.to}: ${msg.message}`);
          }
          break;
        case "conversation_summary":
          addSummary(msg);
          break;
        case "wa_ping":
          addPing({
            ping_id: msg.ping_id,
            contact_id: msg.contact_id,
            contact_name: msg.contact_name,
            preview: msg.preview,
            timestamp: msg.timestamp,
          });
          break;
        case "wa_ping_resolved":
          removePing(msg.ping_id);
          break;
        case "confirm_required":
          useMetherStore.getState().setPendingConfirmation({
            action_id: msg.action_id,
            tool: msg.tool,
            description: msg.description,
            params: msg.params
          });
          break;
        case "action_cancelled": {
          const current = useMetherStore.getState().pendingConfirmation;
          if (current?.action_id === msg.action_id) {
            useMetherStore.getState().setPendingConfirmation(null);
          }
          break;
        }
        case "terminal_line":
          if (msg.line !== undefined) {
            const store = useMetherStore.getState();
            if (!store.terminalOpen) {
              store.clearTerminal();
              store.setTerminalCommand(msg.command || "Executing...");
              store.setTerminalOpen(true);
            }
            store.addTerminalLine({ id: Date.now() + Math.random(), text: msg.line });
          }
          break;
        case "terminal_exit":
          useMetherStore.getState().setTerminalProcessExit(msg.returncode);
          break;
        default:
          addLog("WS", `Unknown message type: ${msg.type}`);
      }
    };

    const scheduleReconnect = () => {
      if (!mountedRef.current) return;
      const delay = Math.min(BASE_DELAY * Math.pow(2, retryCount.current), MAX_DELAY);
      retryCount.current++;
      addLog("WS", `Reconnecting in ${delay / 1000}s (attempt ${retryCount.current})`);
      retryTimer.current = setTimeout(() => {
        if (mountedRef.current) connect();
      }, delay);
    };

    const connect = () => {
      if (!mountedRef.current) return;
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
          if (e.code !== 1000) scheduleReconnect();
        };
        ws.onerror = () => {
          if (!mountedRef.current) return;
          setConnectionStatus("error");
          addLog("WS", "Connection failed — running in demo mode");
          ws.close();
        };
        ws.onmessage = (event) => {
          if (!mountedRef.current) return;
          setLastMessage(event.data);
          try {
            const msg = JSON.parse(event.data) as Record<string, unknown>;
            handleMessage(msg);
          } catch {
            addLog("WS", String(event.data));
          }
        };
      } catch {
        setConnectionStatus("error");
        addLog("WS", "Failed to create WebSocket — running in demo mode");
        scheduleReconnect();
      }
    };

    connect();

    return () => {
      mountedRef.current = false;
      if (retryTimer.current) clearTimeout(retryTimer.current);
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close(1000);
      }
    };
  }, [
    addLog, setOrbState, setActiveTool, incrementStat, setActiveResponse,
    addSummary, addPing, removePing, setLastVoiceHeard, setVoiceLatency,
    setVoiceStatus, setWakeWordTime, wakeWordTime, setConnectionStatus
  ]);

  // Expose send to global store so other components don't have to duplicate connection
  useEffect(() => {
    setSocketSend(send);
    return () => {
      setSocketSend(null);
    };
  }, [send, setSocketSend]);

  return {
    isConnected,
    send,
    lastMessage,
    connectionStatus,
  };
}
