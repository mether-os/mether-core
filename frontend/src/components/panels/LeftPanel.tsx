import React, { useState, useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { useUptime } from "@/hooks/useUptime";
import { useMetherStore } from "@/stores/metherStore";

/* ═══════════════════════════════════════════════════════════════
   METHER OS — Left Panel
   System Vitals (top 30%) + Agent Log terminal (bottom 70%)

   Agent Log now reads from the global Zustand store AND generates
   demo entries when in demo mode, providing a unified feed.
   ═══════════════════════════════════════════════════════════════ */

/* ── Constants ── */
const SEGMENT_COUNT = 10;
const MAX_LOG_DISPLAY = 20;
const LOG_INTERVAL_MS = 1500;
const VITALS_INTERVAL_MS = 2000;

/* ── Log message pool (demo mode) ── */
const LOG_POOL: [string, string][] = [
  ["AGENT", "Reasoning over context..."],
  ["MEMORY", "Fetching from ChromaDB..."],
  ["TOOL", "Calendar.read() executed"],
  ["VOICE", "Wake word detected"],
  ["WS", "Client connected to backend stream"],
  ["LLM", "Token stream started"],
  ["MEMORY", "SQLite write complete"],
  ["TOOL", "Gmail.search() executed"],
  ["AGENT", "Tool result processed"],
  ["SYSTEM", "CPU threshold nominal"],
];

/* ── Module color map ── */
const MODULE_COLORS: Record<string, string> = {
  AGENT: "text-primary",
  MEMORY: "text-secondary",
  TOOL: "text-warning",
  VOICE: "text-[#c084fc]",
  WS: "text-primary-container",
  LLM: "text-primary-fixed-dim",
  SYSTEM: "text-on-surface-variant",
  CMD: "text-primary",
  METHER: "text-primary-fixed",
  WA: "text-success",
  WA_AUTO: "text-success opacity-80",
  GMAIL: "text-blue-400",
  CAL: "text-green-400",
  DRIVE: "text-purple-400",
};

/* ── Helpers ── */
function randomInRange(min: number, max: number): number {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

/* ═══════════════════════════════════════════════════════════════
   SECTION HEADER
   ═══════════════════════════════════════════════════════════════ */
function SectionHeader({ title }: { title: string }) {
  return (
    <div className="flex items-center gap-2 mb-2 shrink-0">
      <span className="w-1 h-3 bg-primary/60" />
      <span className="hud-label text-[10px]">{title}</span>
      <div className="flex-1 h-px bg-primary/10" />
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   SEGMENTED BAR
   ═══════════════════════════════════════════════════════════════ */
function SegmentedBar({ value, max = 100 }: { value: number; max?: number }) {
  const filled = Math.round((value / max) * SEGMENT_COUNT);

  return (
    <div className="flex items-center gap-[2px]">
      {Array.from({ length: SEGMENT_COUNT }, (_, i) => {
        const isActive = i < filled;
        const isLastActive = isActive && i === filled - 1;

        return (
          <div
            key={i}
            className="w-[6px] h-[6px] transition-all duration-300"
            style={{
              background: isActive 
                ? "linear-gradient(90deg, #4cd7f6, #06b6d4)" 
                : "rgba(148, 163, 184, 0.2)",
              boxShadow: isLastActive 
                ? "2px 0 6px rgba(76, 215, 246, 0.6)" 
                : "none",
            }}
          />
        );
      })}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   METRIC ROW
   ═══════════════════════════════════════════════════════════════ */
interface MetricRowProps {
  label: string;
  value: string;
  bar?: number;
  blinkDot?: boolean;
}

function MetricRow({ label, value, bar, blinkDot }: MetricRowProps) {
  return (
    <div className="flex items-center justify-between gap-2 py-[5px]">
      <div className="flex items-center gap-1.5 min-w-[60px]">
        {blinkDot && (
          <span
            className="inline-block w-[5px] h-[5px] rounded-full bg-success"
            style={{ animation: "breathe 2s ease-in-out infinite" }}
          />
        )}
        <span className="text-data-mono text-outline tracking-[0.08em] uppercase">
          {label}
        </span>
      </div>

      {bar !== undefined && <SegmentedBar value={bar} />}

      <span 
        className="text-data-mono tracking-wider text-right min-w-[38px]"
        style={{ color: "#4cd7f6", fontWeight: 700 }}
      >
        {value}
      </span>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   SYSTEM VITALS — Top 30%
   ═══════════════════════════════════════════════════════════════ */
function SystemVitals() {
  const uptime = useUptime();
  const [cpu, setCpu] = useState(32);
  const [ram, setRam] = useState(45);
  const [latency, setLatency] = useState(38);

  useEffect(() => {
    const id = setInterval(() => {
      setCpu((prev) => Math.max(5, Math.min(95, prev + randomInRange(-8, 8))));
      setRam((prev) => Math.max(20, Math.min(90, prev + randomInRange(-5, 5))));
      setLatency(randomInRange(18, 120));
    }, VITALS_INTERVAL_MS);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="shrink-0">
      <SectionHeader title="SYSTEM VITALS" />

      <div className="flex flex-col divide-y divide-primary/[0.08]">
        <MetricRow label="CPU" value={`${cpu}%`} bar={cpu} />
        <MetricRow label="RAM" value={`${ram}%`} bar={ram} />
        <MetricRow label="LATENCY" value={`${latency}ms`} />
        <MetricRow label="UPTIME" value={uptime} />
        <MetricRow label="MODEL" value="GLM-4.7" />
        <MetricRow label="STATUS" value="NOMINAL" blinkDot />
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   AGENT LOG — Bottom 70%
   Reads from global store + generates demo entries.
   ═══════════════════════════════════════════════════════════════ */
export function AgentLog() {
  const storeLogs = useMetherStore((s) => s.logs);
  const addLog = useMetherStore((s) => s.addLog);
  const isDemo = useMetherStore((s) => s.isDemo);
  const scrollRef = useRef<HTMLDivElement>(null);
  const demoSeeded = useRef(false);

  /* Seed initial demo logs */
  useEffect(() => {
    if (demoSeeded.current) return;
    demoSeeded.current = true;
    for (let i = 0; i < 5; i++) {
      const [module, message] = LOG_POOL[i % LOG_POOL.length];
      addLog(module, message);
    }
  }, [addLog]);

  /* Demo mode: add random entries periodically */
  useEffect(() => {
    if (!isDemo) return;

    const id = setInterval(() => {
      const [module, message] = LOG_POOL[Math.floor(Math.random() * LOG_POOL.length)];
      addLog(module, message);
    }, LOG_INTERVAL_MS);

    return () => clearInterval(id);
  }, [isDemo, addLog]);

  /* Auto-scroll to bottom */
  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [storeLogs]);

  /* Display last N entries */
  const visibleLogs = storeLogs.slice(-MAX_LOG_DISPLAY);

  return (
    <div className="flex flex-col flex-1 min-h-0">
      <SectionHeader title="AGENT LOG" />

      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto overflow-x-hidden min-h-0"
        style={{
          scrollbarWidth: "none",
          maskImage:
            "linear-gradient(to bottom, transparent 0%, black 8%, black 100%)",
          WebkitMaskImage:
            "linear-gradient(to bottom, transparent 0%, black 8%, black 100%)",
        }}
      >
        <div className="flex flex-col gap-[2px]">
          {visibleLogs.map((entry) => (
            <LogLine key={entry.id} entry={entry} />
          ))}
        </div>
      </div>
    </div>
  );
}

/* ── Log line ── */
const MODULE_BORDER_COLORS: Record<string, string> = {
  VOICE: 'rgba(139,92,246,0.8)',
  AGENT: 'rgba(76,215,246,0.8)',
  WS: 'rgba(16,185,129,0.6)',
  TOOL: 'rgba(245,158,11,0.7)',
  LLM: 'rgba(76,215,246,0.5)',
  MEMORY: 'rgba(139,92,246,0.5)',
  SYSTEM: 'rgba(148,163,184,0.4)',
  CMD: 'rgba(76,215,246,0.6)',
  METHER: 'rgba(76,215,246,0.7)',
  WA: 'rgba(16,185,129,0.7)',
  WA_AUTO: 'rgba(16,185,129,0.5)',
  GMAIL: 'rgba(96,165,250,0.6)',
  CAL: 'rgba(74,222,128,0.6)',
  DRIVE: 'rgba(167,139,250,0.6)',
}

function LogLine({ entry }: { entry: { id: number; time: string; module: string; message: string } }) {
  const moduleColor = MODULE_COLORS[entry.module] ?? "text-outline";
  const borderColor = MODULE_BORDER_COLORS[entry.module] ?? 'rgba(148,163,184,0.3)';

  return (
    <motion.div
      initial={{ opacity: 0, x: -4 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.2, ease: 'easeOut' }}
      className="text-[9px] font-mono leading-[1.7] flex gap-[6px] items-center log-entry-hover px-1 -mx-1 rounded-sm overflow-hidden text-ellipsis"
      title={`[${entry.time}] [${entry.module}] ${entry.message}`}
      style={{
        borderLeft: `2px solid ${borderColor}`,
        paddingLeft: '6px',
      }}
    >
      <span className="shrink-0" style={{ color: "rgba(76, 215, 246, 0.3)", minWidth: "60px" }}>
        [{entry.time}]
      </span>{" "}
      <span className={`${moduleColor} shrink-0 font-bold`} style={{ width: "52px" }}>
        [{entry.module}]
      </span>{" "}
      <span className="truncate flex-1" style={{ color: "rgba(76, 215, 246, 0.65)" }}>
        {entry.message}
      </span>
    </motion.div>
  );
}

function ConversationSummaryCard({ summary, onDismiss }: { summary: Record<string, unknown>, onDismiss: () => void }) {
  return (
    <div className="hud-panel border border-warning/50 bg-warning/5 p-2 mb-2 relative animate-type-in shrink-0">
      <button onClick={onDismiss} className="absolute top-1 right-2 text-outline-variant hover:text-warning text-[10px]">✕</button>
      <div className="text-[10px] font-mono text-warning font-bold mb-1">[CONVERSATION SUMMARY] {String(summary.contact ?? "")}</div>
      <div className="text-[9px] font-mono text-on-surface-variant whitespace-pre-wrap leading-relaxed">
        {String(summary.summary ?? "")}
      </div>
      <div className="mt-1 flex justify-between text-[8px] text-outline-variant font-mono">
        <span>Msgs: {String(summary.message_count ?? "")}</span>
        <span>Dur: {String(summary.duration ?? "")}</span>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   LEFT PANEL — Main Export
   ═══════════════════════════════════════════════════════════════ */
const LeftPanel = () => {
  const summaries = useMetherStore(s => s.summaries);
  const dismissSummary = useMetherStore(s => s.dismissSummary);

  return (
    <div 
      className="hud-panel hud-corner-bracket flex-1 flex flex-col min-h-0 !p-3 bg-surface-container"
      style={{
        borderRight: "1px solid rgba(76,215,246,0.12)",
        boxShadow: "inset -1px 0 12px rgba(76,215,246,0.03)",
      }}
    >
      <span className="hud-corner-bracket--extra absolute inset-0 pointer-events-none" />

      <SystemVitals />

      <div className="my-2 h-px bg-primary/15 shrink-0" />
      
      {summaries.map((sum, i) => (
        <ConversationSummaryCard key={i} summary={sum} onDismiss={() => dismissSummary(i)} />
      ))}

      <AgentLog />
    </div>
  );
}

export default React.memo(LeftPanel);
