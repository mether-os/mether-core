import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import { useUptime } from "@/hooks/useUptime";

/* ═══════════════════════════════════════════════════════════════
   METHER OS — Left Panel
   System Vitals (top 30%) + Agent Log terminal (bottom 70%)
   ═══════════════════════════════════════════════════════════════ */

/* ── Constants ── */
const SEGMENT_COUNT = 10;
const MAX_LOG_ENTRIES = 20;
const LOG_INTERVAL_MS = 1500;
const VITALS_INTERVAL_MS = 2000;

/* ── Log message pool ── */
const LOG_POOL: [string, string][] = [
  ["AGENT", "Reasoning over context..."],
  ["MEMORY", "Fetching from ChromaDB..."],
  ["TOOL", "Calendar.read() executed"],
  ["VOICE", "Wake word detected"],
  ["WS", "Client connected on port 8000"],
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
  VOICE: "text-success",
  WS: "text-primary-container",
  LLM: "text-primary-fixed-dim",
  SYSTEM: "text-on-surface-variant",
};

/* ── Helpers ── */
function timestamp(): string {
  return new Date().toLocaleTimeString("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

function randomInRange(min: number, max: number): number {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

/* ═══════════════════════════════════════════════════════════════
   SECTION HEADER — Reusable panel section title
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
   SEGMENTED BAR — [■■■■□□□□□□] progress visualization
   ═══════════════════════════════════════════════════════════════ */
function SegmentedBar({ value, max = 100 }: { value: number; max?: number }) {
  const filled = Math.round((value / max) * SEGMENT_COUNT);

  return (
    <div className="flex items-center gap-[2px]">
      {Array.from({ length: SEGMENT_COUNT }, (_, i) => (
        <div
          key={i}
          className={`w-[6px] h-[6px] transition-colors duration-300 ${
            i < filled
              ? value > 80
                ? "bg-error/80"
                : value > 60
                  ? "bg-warning/70"
                  : "bg-primary/60"
              : "bg-outline-variant/20"
          }`}
        />
      ))}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   METRIC ROW — Label + value + optional bar
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
      {/* Label */}
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

      {/* Bar (optional) */}
      {bar !== undefined && <SegmentedBar value={bar} />}

      {/* Value */}
      <span className="text-data-mono text-primary font-bold tracking-wider text-right min-w-[38px]">
        {value}
      </span>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   SYSTEM VITALS — Top 30% of panel
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
   AGENT LOG — Bottom 70% of panel (scrolling terminal feed)
   ═══════════════════════════════════════════════════════════════ */
interface LogEntry {
  id: number;
  time: string;
  module: string;
  message: string;
}

function AgentLog() {
  const [entries, setEntries] = useState<LogEntry[]>([]);
  const nextId = useRef(0);
  const scrollRef = useRef<HTMLDivElement>(null);

  /* Pick a random log */
  const pickRandom = useCallback((): LogEntry => {
    const [module, message] = LOG_POOL[Math.floor(Math.random() * LOG_POOL.length)];
    return { id: nextId.current++, time: timestamp(), module, message };
  }, []);

  /* Seed initial entries */
  const initialEntries = useMemo(() => {
    const seed: LogEntry[] = [];
    for (let i = 0; i < 5; i++) {
      const [module, message] = LOG_POOL[i % LOG_POOL.length];
      seed.push({ id: nextId.current++, time: timestamp(), module, message });
    }
    return seed;
  }, []);

  useEffect(() => {
    setEntries(initialEntries);
  }, [initialEntries]);

  /* Add new entries on interval */
  useEffect(() => {
    const id = setInterval(() => {
      setEntries((prev) => {
        const next = [...prev, pickRandom()];
        return next.length > MAX_LOG_ENTRIES ? next.slice(-MAX_LOG_ENTRIES) : next;
      });
    }, LOG_INTERVAL_MS);
    return () => clearInterval(id);
  }, [pickRandom]);

  /* Auto-scroll to bottom */
  useEffect(() => {
    const el = scrollRef.current;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  }, [entries]);

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
          {entries.map((entry) => (
            <LogLine key={entry.id} entry={entry} />
          ))}
        </div>
      </div>
    </div>
  );
}

/* ── Single log line with typewriter entrance ── */
function LogLine({ entry }: { entry: LogEntry }) {
  const moduleColor = MODULE_COLORS[entry.module] ?? "text-outline";

  return (
    <div
      className="text-[9px] font-mono leading-[1.7] whitespace-nowrap
                 overflow-hidden animate-type-in"
    >
      <span className="text-outline-variant">[{entry.time}]</span>{" "}
      <span className={`${moduleColor} font-bold`}>[{entry.module}]</span>{" "}
      <span className="text-on-surface-variant">{entry.message}</span>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   LEFT PANEL — Main Export
   Composes vitals + log inside a corner-bracketed frame.
   ═══════════════════════════════════════════════════════════════ */
export default function LeftPanel() {
  return (
    <div className="hud-panel hud-corner-bracket flex-1 flex flex-col min-h-0 !p-3 bg-surface-container">
      {/* Extra corners (top-right + bottom-left) */}
      <span className="hud-corner-bracket--extra absolute inset-0 pointer-events-none" />

      {/* Section 1 — System Vitals (top ~30%) */}
      <SystemVitals />

      {/* Divider */}
      <div className="my-2 h-px bg-primary/15 shrink-0" />

      {/* Section 2 — Agent Log (bottom ~70%) */}
      <AgentLog />
    </div>
  );
}
