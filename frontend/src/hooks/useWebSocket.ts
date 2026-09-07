import React, { useEffect, useRef, useCallback } from "react";
import { useMetherStore } from "@/stores/metherStore";
import { useResearchStore } from "@/stores/researchStore";
import { useChiefOfStaffStore } from "@/stores/chiefOfStaffStore";
import type { ConnectionStatus } from "@/stores/metherStore";
import config from "../config";

const WS_URL = config.wsUrl;
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
            } else if (msg.state === "speaking") {
              const currentWakeWordTime = useMetherStore.getState().wakeWordTime;
              if (currentWakeWordTime) {
                setVoiceLatency(Date.now() - currentWakeWordTime);
              }
            }
          }
          break;
        case "log": {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const payload = msg as any;
          if (payload.module && payload.message) {
            addLog(payload.module, payload.message);
            if (payload.module === "VOICE" && payload.message.startsWith("Heard: ")) {
              setLastVoiceHeard(payload.message.replace("Heard: ", ""));
            }
          }
          break;
        }
        case "response":
          if (typeof msg.text === "string") {
            setActiveResponse(msg.source === "voice" ? `[VOICE] ${msg.text}` : msg.text);
            if (msg.source === "voice") {
              const currentWakeWordTime = useMetherStore.getState().wakeWordTime;
              if (currentWakeWordTime) {
                setVoiceLatency(Date.now() - currentWakeWordTime);
              }
            }
          }
          break;
        case "voice_status":
          if (typeof msg.status === "string" && (msg.status === "online" || msg.status === "offline")) {
            setVoiceStatus(msg.status);
          }
          break;
        case "agent.thinking":
          break;
        case "tool.start": {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const payload = msg as any;
          if (payload.data && payload.data.tool) {
            setActiveTool(payload.data.tool);
            addLog("TOOL", `Active: ${payload.data.tool}`);
          }
          break;
        }
        case "tool.done": {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const payload = msg as any;
          if (payload.data && payload.data.tool) {
            addLog("TOOL", `Done: ${payload.data.tool}`);
            setActiveTool("STANDBY");
          }
          break;
        }
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
        case "wa_ping": {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const payload = msg as any;
          addPing({
            ping_id: payload.ping_id,
            contact_id: payload.contact_id,
            contact_name: payload.contact_name,
            preview: payload.preview,
            timestamp: payload.timestamp,
          });
          break;
        }
        case "wa_ping_resolved": {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const payload = msg as any;
          removePing(payload.ping_id);
          break;
        }
        case "confirm_required": {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const payload = msg as any;
          useMetherStore.getState().setPendingConfirmation({
            action_id: payload.action_id,
            tool: payload.tool,
            description: payload.description,
            params: payload.params
          });
          break;
        }
        case "action_cancelled": {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const payload = msg as any;
          const current = useMetherStore.getState().pendingConfirmation;
          if (current?.action_id === payload.action_id) {
            useMetherStore.getState().setPendingConfirmation(null);
          }
          break;
        }
        case "terminal_line": {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const payload = msg as any;
          if (payload.line !== undefined) {
            const store = useMetherStore.getState();
            if (!store.terminalOpen) {
              store.clearTerminal();
              store.setTerminalCommand(payload.command || "Executing...");
              store.setTerminalOpen(true);
            }
            store.addTerminalLine({ id: Date.now() + Math.random(), text: payload.line });
          }
          break;
        }
        case "terminal_exit": {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const payload = msg as any;
          useMetherStore.getState().setTerminalProcessExit(payload.returncode);
          break;
        }
        case "whatsapp_status":
          if (typeof msg.status === "string" && (msg.status === "connected" || msg.status === "disconnected")) {
            useMetherStore.getState().setWhatsappStatus(msg.status);
            if (msg.status === "connected") {
              useMetherStore.getState().setWhatsappQR(null);
            }
          }
          break;
        case "whatsapp_qr":
          if (typeof msg.qr === "string" || msg.qr === null) {
            useMetherStore.getState().setWhatsappQR(msg.qr);
          }
          break;
        case "research_progress": {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const payload = msg as any;
          if (payload.task_id) {
            const store = useResearchStore.getState();
            store.setActiveTaskId(payload.task_id);
            store.setProgressMessage(payload.message || "");
            
            store.setTaskState({
              id: payload.task_id,
              topic: payload.topic || store.taskState?.topic || "Research Task",
              status: payload.status || "running",
              stage: payload.stage || "collecting",
              depth: payload.depth || store.taskState?.depth || "deep",
              length_target: payload.length_target || store.taskState?.length_target || "20_pages",
              progress_percent: payload.progress || 0.0,
              estimated_completion_time: payload.eta || null,
              output_path: payload.output_path || null,
              error_message: payload.error_message || null,
              research_mode: payload.research_mode || store.taskState?.research_mode || "balanced",
              target_audience: payload.target_audience || store.taskState?.target_audience || "researcher",
              human_review_enabled: payload.human_review_enabled ?? store.taskState?.human_review_enabled ?? 0,
            });
            
            if (payload.details && payload.details.outline) {
              store.setSections(payload.details.outline);
            }
            if (payload.details && payload.details.sections) {
              store.setSections(payload.details.sections);
            }
            
            addLog("AGENT", `[RESEARCH] ${payload.message}`);
          }
          break;
        }
        case "cos_progress": {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const payload = msg as any;
          const store = useChiefOfStaffStore.getState();
          store.setProgressMessage(payload.message || "");
          store.setProgressPercent(payload.progress || 0.0);
          addLog("AGENT", `[CHIEF OF STAFF] ${payload.message}`);
          break;
        }
        case "cos_update": {
          const store = useChiefOfStaffStore.getState();
          const headers: Record<string, string> = { "Content-Type": "application/json" };
          if (config.apiKey) {
            headers["X-METHER-KEY"] = config.apiKey;
          }
          fetch(`${config.backendUrl}/api/v1/cos/dashboard`, { headers })
            .then(res => res.json())
            .then(data => {
              if (data) {
                store.setGoals(data.goals || []);
                store.setDaily(data.daily || null);
                store.setReview(data.review || null);
                store.setRecommendations(data.recommendations || "");
                store.setStats(data.stats || null);
              }
            })
            .catch(err => console.error("Failed to sync COS WebSocket update:", err));
          break;
        }
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
      // Mark as unmounted FIRST so no callbacks fire after this point
      mountedRef.current = false;
      if (retryTimer.current) {
        clearTimeout(retryTimer.current);
        retryTimer.current = null;
      }
      const ws = wsRef.current;
      if (ws) {
        // Null out all handlers before closing to prevent onclose re-triggering reconnects
        ws.onopen = null;
        ws.onclose = null;
        ws.onmessage = null;
        ws.onerror = null;
        if (ws.readyState === WebSocket.CONNECTING || ws.readyState === WebSocket.OPEN) {
          ws.close(1000);
        }
        wsRef.current = null;
      }
    };
  }, [
    addLog, setOrbState, setActiveTool, incrementStat, setActiveResponse,
    addSummary, addPing, removePing, setLastVoiceHeard, setVoiceLatency,
    setVoiceStatus, setWakeWordTime, setConnectionStatus
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
