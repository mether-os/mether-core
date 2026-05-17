import { create } from "zustand";

/* ═══════════════════════════════════════════════════════════════
   METHER OS — Global State Store (Zustand)

   Single source of truth for:
   • Orb state           • WebSocket connection
   • Logs / terminal     • Command history
   • Session stats       • Active tools
   ═══════════════════════════════════════════════════════════════ */

/* ── Types ── */
export type OrbState = "sleeping" | "idle" | "listening" | "processing" | "speaking";
export type ConnectionStatus = "connecting" | "connected" | "disconnected" | "error";

export interface LogEntry {
  id: number;
  time: string;
  module: string;
  message: string;
}

export interface SessionStats {
  commands: number;
  toolsUsed: number;
  memoryHits: number;
  tokens: number;
}

export interface WAPing {
  ping_id: string;
  contact_id: string;
  contact_name: string;
  preview: string;
  timestamp: number;
}

/* ── Store interface ── */
interface MetherState {
  /* Voice Orb & Pipeline */
  orbState: OrbState;
  setOrbState: (s: OrbState) => void;
  voiceStatus: "offline" | "online";
  setVoiceStatus: (s: "offline" | "online") => void;
  lastVoiceHeard: string;
  setLastVoiceHeard: (s: string) => void;
  voiceLatency: number | null;
  setVoiceLatency: (n: number | null) => void;
  wakeWordTime: number | null;
  setWakeWordTime: (n: number | null) => void;

  /* WebSocket */
  connectionStatus: ConnectionStatus;
  setConnectionStatus: (s: ConnectionStatus) => void;
  isConnected: boolean;

  /* Logs */
  logs: LogEntry[];
  addLog: (module: string, message: string) => void;
  clearLogs: () => void;

  /* Commands */
  commandHistory: string[];
  addCommand: (cmd: string) => void;

  /* Active tools */
  activeTools: string[];
  setActiveTools: (tools: string[]) => void;
  activeTool: string;
  setActiveTool: (tool: string) => void;

  /* Session stats */
  sessionStats: SessionStats;
  incrementStat: (key: keyof SessionStats, amount?: number) => void;

  /* Demo mode */
  isDemo: boolean;
  setDemo: (on: boolean) => void;

  /* Response Display */
  activeResponse: string | null;
  setActiveResponse: (res: string | null) => void;

  /* WhatsApp Summaries */
  summaries: any[];
  addSummary: (summary: any) => void;
  dismissSummary: (index: number) => void;

  /* WhatsApp Auto-handle & Pings */
  waActivePings: WAPing[];
  waHandledContacts: string[];
  addPing: (ping: WAPing) => void;
  removePing: (ping_id: string) => void;
  addHandledContact: (contact_id: string) => void;
  removeHandledContact: (contact_id: string) => void;

  /* Global WebSocket Send */
  socketSend: ((msg: string) => void) | null;
  setSocketSend: (sendFn: ((msg: string) => void) | null) => void;
}

/* ── Helpers ── */
let _nextLogId = 0;

function timestamp(): string {
  return new Date().toLocaleTimeString("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

const MAX_LOGS = 50;
const MAX_HISTORY = 10;

/* ── Store ── */
export const useMetherStore = create<MetherState>((set) => ({
  /* Voice Orb & Pipeline */
  orbState: "idle",
  setOrbState: (s) => set({ orbState: s }),
  voiceStatus: "offline",
  setVoiceStatus: (s) => set({ voiceStatus: s }),
  lastVoiceHeard: "",
  setLastVoiceHeard: (s) => set({ lastVoiceHeard: s }),
  voiceLatency: null,
  setVoiceLatency: (n) => set({ voiceLatency: n }),
  wakeWordTime: null,
  setWakeWordTime: (n) => set({ wakeWordTime: n }),

  /* WebSocket */
  connectionStatus: "disconnected",
  setConnectionStatus: (s) =>
    set({ connectionStatus: s, isConnected: s === "connected" }),
  isConnected: false,

  /* Logs */
  logs: [],
  addLog: (module, message) =>
    set((state) => {
      const entry: LogEntry = {
        id: _nextLogId++,
        time: timestamp(),
        module,
        message,
      };
      const next = [...state.logs, entry];
      return { logs: next.length > MAX_LOGS ? next.slice(-MAX_LOGS) : next };
    }),
  clearLogs: () => set({ logs: [] }),

  /* Commands */
  commandHistory: [],
  addCommand: (cmd) =>
    set((state) => {
      const next = [...state.commandHistory, cmd];
      return {
        commandHistory: next.length > MAX_HISTORY ? next.slice(-MAX_HISTORY) : next,
      };
    }),

  /* Active tools */
  activeTools: [],
  setActiveTools: (tools) => set({ activeTools: tools }),
  activeTool: "STANDBY",
  setActiveTool: (tool) => set({ activeTool: tool }),

  /* Session stats */
  sessionStats: { commands: 0, toolsUsed: 0, memoryHits: 0, tokens: 0 },
  incrementStat: (key, amount = 1) =>
    set((state) => ({
      sessionStats: {
        ...state.sessionStats,
        [key]: state.sessionStats[key] + amount,
      },
    })),

  /* Demo */
  isDemo: true,
  setDemo: (on) => set({ isDemo: on }),

  /* Response Display */
  activeResponse: null,
  setActiveResponse: (res) => set({ activeResponse: res }),

  /* WhatsApp Summaries */
  summaries: [],
  addSummary: (summary) => set((state) => ({ summaries: [...state.summaries, summary] })),
  dismissSummary: (index) => set((state) => ({
    summaries: state.summaries.filter((_, i) => i !== index)
  })),

  /* WhatsApp Pings */
  waActivePings: [],
  waHandledContacts: [],
  addPing: (ping) =>
    set((state) => ({ waActivePings: [...state.waActivePings, ping] })),
  removePing: (ping_id) =>
    set((state) => ({
      waActivePings: state.waActivePings.filter((p) => p.ping_id !== ping_id),
    })),
  addHandledContact: (contact_id) =>
    set((state) => ({
      waHandledContacts: state.waHandledContacts.includes(contact_id)
        ? state.waHandledContacts
        : [...state.waHandledContacts, contact_id],
    })),
  removeHandledContact: (contact_id) =>
    set((state) => ({
      waHandledContacts: state.waHandledContacts.filter((id) => id !== contact_id),
    })),

  /* WebSocket send */
  socketSend: null,
  setSocketSend: (sendFn) => set({ socketSend: sendFn }),
}));
