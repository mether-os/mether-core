import React, { useState, useEffect, useRef, useMemo } from "react";
import { useMetherStore } from "@/stores/metherStore";
import { useResearchStore } from "@/stores/researchStore";
import config from "../../config";

/* ═══════════════════════════════════════════════════════════════
   METHER OS — Right Panel
   Proximity Radar (35%) + Objectives (35%) + Session Stats (30%)
   ═══════════════════════════════════════════════════════════════ */

/* ── Constants ── */
const SEGMENT_COUNT = 10;
const RADAR_SIZE = 220;
const RADAR_CENTER = RADAR_SIZE / 2;
const SWEEP_DURATION = 3; // seconds per full rotation

/* ── Helpers (kept for potential future use) ── */

/* ═══════════════════════════════════════════════════════════════
   SECTION HEADER — Reusable panel section title
   (mirrors LeftPanel's SectionHeader)
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
   SEGMENTED BAR — [■■■■□□□□□□]
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
            className="w-[5px] h-[5px] transition-all duration-300"
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
   SECTION 1 — Proximity Radar (SVG)
   ═══════════════════════════════════════════════════════════════ */

interface Blip {
  id: number;
  label: string;
  angle: number; // degrees
  radius: number; // 0–1 normalized
  speed: number; // deg/s drift
}

function ProximityRadar() {
  const [sweepAngle, setSweepAngle] = useState(0);
  const animRef = useRef<number>(0);
  const lastTime = useRef<number>(0);

  const isConnected = useMetherStore((s) => s.isConnected);
  const whatsappStatus = useMetherStore((s) => s.whatsappStatus);
  const voiceStatus = useMetherStore((s) => s.voiceStatus);
  const googleAuthStatus = useMetherStore((s) => s.googleAuthStatus);

  /* ── Generate blips once ── */
  const blips = useMemo<Blip[]>(() => {
    return [
      { id: 0, label: "SYS", angle: 45, radius: 0.4, speed: 0.5 },
      { id: 1, label: "WA", angle: 120, radius: 0.7, speed: 0.8 },
      { id: 2, label: "VOIC", angle: 210, radius: 0.3, speed: 0.4 },
      { id: 3, label: "GGL", angle: 300, radius: 0.8, speed: 1.1 },
      { id: 4, label: "LLM", angle: 15, radius: 0.6, speed: 0.6 }
    ];
  }, []);

  /* ── Blip drift state ── */
  const [blipAngles, setBlipAngles] = useState(() => blips.map((b) => b.angle));

  const getIsActive = (id: number) => {
    switch (id) {
      case 0: return isConnected;
      case 1: return whatsappStatus === "connected";
      case 2: return voiceStatus === "online";
      case 3: return googleAuthStatus;
      case 4: return isConnected;
      default: return false;
    }
  };

  /* ── Animation loop ── */
  useEffect(() => {
    const tick = (time: number) => {
      if (!lastTime.current) lastTime.current = time;
      const dt = (time - lastTime.current) / 1000;
      lastTime.current = time;

      setSweepAngle((prev) => (prev + (360 / SWEEP_DURATION) * dt) % 360);
      setBlipAngles((prev) =>
        prev.map((a, i) => (a + blips[i].speed * dt) % 360)
      );

      animRef.current = requestAnimationFrame(tick);
    };

    animRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(animRef.current);
  }, [blips]);

  const ringRadii = [0.3, 0.6, 0.9]; // normalized
  const maxR = RADAR_CENTER - 8;

  return (
    <div className="shrink-0">
      <SectionHeader title="PROXIMITY SCAN" />

      <div className="flex justify-center">
        <svg
          width={RADAR_SIZE}
          height={RADAR_SIZE}
          viewBox={`0 0 ${RADAR_SIZE} ${RADAR_SIZE}`}
          className="overflow-visible"
        >
          <defs>
            {/* Sweep trail gradient */}
            <linearGradient id="sweepGrad" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="rgba(76, 215, 246, 0)" />
              <stop offset="100%" stopColor="rgba(76, 215, 246, 0.3)" />
            </linearGradient>

            {/* Blip glow filter */}
            <filter id="blipGlow">
              <feGaussianBlur stdDeviation="1.5" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* ── Range rings ── */}
          {ringRadii.map((r, i) => (
            <circle
              key={i}
              cx={RADAR_CENTER}
              cy={RADAR_CENTER}
              r={r * maxR}
              fill="none"
              stroke="rgba(76, 215, 246, 0.12)"
              strokeWidth="1"
            />
          ))}

          {/* ── Crosshair lines ── */}
          <line
            x1={RADAR_CENTER}
            y1={8}
            x2={RADAR_CENTER}
            y2={RADAR_SIZE - 8}
            stroke="rgba(76, 215, 246, 0.08)"
            strokeWidth="1"
          />
          <line
            x1={8}
            y1={RADAR_CENTER}
            x2={RADAR_SIZE - 8}
            y2={RADAR_CENTER}
            stroke="rgba(76, 215, 246, 0.08)"
            strokeWidth="1"
          />

          {/* ── Degree labels ── */}
          {[
            { deg: 0, x: RADAR_CENTER, y: 6, anchor: "middle" as const },
            { deg: 90, x: RADAR_SIZE - 2, y: RADAR_CENTER + 3, anchor: "end" as const },
            { deg: 180, x: RADAR_CENTER, y: RADAR_SIZE - 1, anchor: "middle" as const },
            { deg: 270, x: 4, y: RADAR_CENTER + 3, anchor: "start" as const },
          ].map((m) => (
            <text
              key={m.deg}
              x={m.x}
              y={m.y}
              textAnchor={m.anchor}
              fill="rgba(76, 215, 246, 0.35)"
              fontSize="7"
              fontFamily="JetBrains Mono, monospace"
            >
              {m.deg}°
            </text>
          ))}

          {/* ── Sweep cone (fading trail) ── */}
          <g transform={`rotate(${sweepAngle}, ${RADAR_CENTER}, ${RADAR_CENTER})`}>
            {/* Trail arc — 40 degree wedge */}
            <path
              d={(() => {
                const r = maxR * 0.9;
                const startAngle = -40 * (Math.PI / 180);
                const endAngle = 0;
                const x1 = RADAR_CENTER + r * Math.sin(startAngle);
                const y1 = RADAR_CENTER - r * Math.cos(startAngle);
                const x2 = RADAR_CENTER + r * Math.sin(endAngle);
                const y2 = RADAR_CENTER - r * Math.cos(endAngle);
                return `M ${RADAR_CENTER} ${RADAR_CENTER} L ${x1} ${y1} A ${r} ${r} 0 0 1 ${x2} ${y2} Z`;
              })()}
              fill="url(#sweepGrad)"
              opacity="0.6"
            />

            {/* Sweep line */}
            <line
              x1={RADAR_CENTER}
              y1={RADAR_CENTER}
              x2={RADAR_CENTER}
              y2={RADAR_CENTER - maxR * 0.9}
              stroke="rgba(76, 215, 246, 0.7)"
              strokeWidth="1.5"
            />
          </g>

          {/* ── Center dot ── */}
          <rect
            x={RADAR_CENTER - 2.5}
            y={RADAR_CENTER - 2.5}
            width="5"
            height="5"
            fill="#4cd7f6"
            filter="url(#blipGlow)"
          />

          {/* ── Blips ── */}
          {blips.map((blip, i) => {
            const a = (blipAngles[i] - 90) * (Math.PI / 180);
            const r = blip.radius * maxR;
            const bx = RADAR_CENTER + r * Math.cos(a);
            const by = RADAR_CENTER + r * Math.sin(a);

            // Brightness based on sweep proximity
            const angleDiff = Math.abs(
              ((sweepAngle - blipAngles[i] + 540) % 360) - 180
            );
            const brightness = angleDiff < 30 ? 1 : Math.max(0.15, 1 - angleDiff / 180);
            const isActive = getIsActive(blip.id);

            return (
              <g key={blip.id}>
                <polygon
                  points={`${bx},${by - 4} ${bx + 4},${by} ${bx},${by + 4} ${bx - 4},${by}`}
                  fill={isActive ? `rgba(76, 215, 246, ${brightness})` : `rgba(239, 68, 68, ${brightness * 0.45})`}
                  filter={isActive && brightness > 0.5 ? "url(#blipGlow)" : undefined}
                />
                <text
                  x={bx + 6}
                  y={by + 2}
                  fill={isActive ? `rgba(76, 215, 246, ${brightness * 0.8})` : `rgba(239, 68, 68, ${brightness * 0.5})`}
                  fontSize="6"
                  fontFamily="JetBrains Mono, monospace"
                  className="font-bold tracking-wider"
                >
                  {blip.label}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   SECTION 2 — Active Objectives
   ═══════════════════════════════════════════════════════════════ */

interface Objective {
  name: string;
  progress: number;
  status: "IN PROGRESS" | "PENDING" | "COMPLETE";
}


function ObjectiveItem({ obj }: { obj: Objective }) {
  const chipClass =
    obj.status === "IN PROGRESS"
      ? "hud-chip hud-chip--success"
      : obj.status === "COMPLETE"
        ? "hud-chip hud-chip--success font-bold"
        : "hud-chip hud-chip--warning";

  return (
    <div className="py-[6px]">
      {/* Name + chip */}
      <div className="flex items-center justify-between gap-1 mb-1">
        <span className="text-data-mono text-on-surface-variant uppercase tracking-wider truncate text-[9px]">
          {obj.name}
        </span>
        <span className={`${chipClass} !text-[7px] !py-0 !px-1.5 !gap-1 shrink-0`}>
          {obj.status}
        </span>
      </div>

      {/* Bar + percentage */}
      <div className="flex items-center gap-2">
        <SegmentedBar value={obj.progress} />
        <span className="text-data-mono text-primary font-bold text-[10px] min-w-[26px] text-right">
          {obj.progress}%
        </span>
      </div>
    </div>
  );
}

function ActiveObjectives() {
  const [objectives, setObjectives] = useState<Objective[]>([]);

  useEffect(() => {
    const fetchObjectives = async () => {
      const headers: Record<string, string> = {};
      if (config.apiKey) {
        headers["X-METHER-KEY"] = config.apiKey;
      }
      try {
        const res = await fetch(`${config.backendUrl}/api/v1/objectives`, { headers });
        if (res.ok) {
          const data = await res.json();
          if (Array.isArray(data.objectives)) {
            setObjectives(data.objectives);
          }
        }
      } catch {
        // Backend offline
      }
    };

    fetchObjectives();
    const id = setInterval(fetchObjectives, 10000);
    return () => clearInterval(id);
  }, []);

  const displayObjectives = objectives.length > 0 ? objectives : [
    { name: "BUILD METHER CORE", progress: 85, status: "IN PROGRESS" as const },
    { name: "CONNECT VOICE PIPELINE", progress: 0, status: "PENDING" as const },
    { name: "WHATSAPP BRIDGE", progress: 0, status: "PENDING" as const },
  ];

  return (
    <div className="shrink-0">
      <SectionHeader title="OBJECTIVES" />
      <div className="flex flex-col divide-y divide-primary/[0.08]">
        {displayObjectives.map((obj) => (
          <ObjectiveItem key={obj.name} obj={obj} />
        ))}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   SECTION 3 — Voice Pipeline (Replaces Session Stats)
   ═══════════════════════════════════════════════════════════════ */

function VoicePipeline() {
  const voiceStatus = useMetherStore((s) => s.voiceStatus);
  const lastVoiceHeard = useMetherStore((s) => s.lastVoiceHeard);
  const voiceLatency = useMetherStore((s) => s.voiceLatency);

  return (
    <div className="shrink-0">
      <SectionHeader title="VOICE PIPELINE" />

      <div className="flex flex-col divide-y divide-primary/[0.08]">
        <StatRow 
          label="WAKE WORD" 
          value={voiceStatus === "online" ? "ACTIVE" : "INACTIVE"} 
          blink={voiceStatus === "online"} 
        />
        <StatRow label="STT MODEL" value="Whisper base" />
        <StatRow label="TTS ENGINE" value="Piper" />
        <StatRow 
          label="LAST HEARD" 
          value={lastVoiceHeard ? (lastVoiceHeard.length > 25 ? lastVoiceHeard.substring(0, 25) + "..." : lastVoiceHeard) : "--"} 
        />
        <StatRow label="LATENCY" value={voiceLatency ? `${voiceLatency}ms` : "--"} />
      </div>
    </div>
  );
}

function StatRow({
  label,
  value,
  blink,
}: {
  label: string;
  value: string;
  blink?: boolean;
}) {
  return (
    <div className="flex items-center justify-between py-[5px]">
      <span className="text-data-mono text-outline tracking-[0.08em] uppercase">
        {label}
      </span>
      <div className="flex items-center gap-1.5">
        {blink && (
          <span 
            className="w-1.5 h-1.5 rounded-full bg-success animate-pulse"
            style={{ boxShadow: "0 0 6px rgba(34,197,94,0.6)" }}
          />
        )}
        <span
          className={`text-data-mono font-bold tracking-wider ${
            blink
              ? "text-success"
              : "text-primary"
          }`}
          style={blink ? { animation: "breathe 1.5s ease-in-out infinite" } : undefined}
        >
          {value}
        </span>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   SECTION 4 — Google Services
   ═══════════════════════════════════════════════════════════════ */

function GoogleServices() {
  const [status, setStatus] = useState<Record<string, unknown> | null>(null);

  const fetchStatus = async () => {
    const headers: Record<string, string> = {};
    if (config.apiKey) {
      headers["X-METHER-KEY"] = config.apiKey;
    }
    try {
      const res = await fetch(`${config.backendUrl}/api/v1/google/status`, { headers });
      const data = await res.json();
      setStatus(data);
      useMetherStore.getState().setGoogleAuthStatus(!!data.authenticated);
    } catch {
      setStatus({ authenticated: false });
      useMetherStore.getState().setGoogleAuthStatus(false);
    }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchStatus();
    const id = setInterval(fetchStatus, 30000);
    return () => clearInterval(id);
  }, []);

  const handleConnect = async () => {
    const headers: Record<string, string> = {};
    if (config.apiKey) {
      headers["X-METHER-KEY"] = config.apiKey;
    }
    try {
      const res = await fetch(`${config.backendUrl}/api/v1/google/auth/url`, { headers });
      const data = await res.json();
      if (data.url) {
        window.location.href = data.url;
      }
    } catch (err) {
      console.error(err);
    }
  };

  if (!status) return null;

  if (!status.authenticated) {
    return (
      <div className="shrink-0">
        <SectionHeader title="GOOGLE SERVICES" />
        <div className="flex items-center justify-between py-[5px]">
          <div className="flex items-center gap-1.5 min-w-[60px]">
            <span className="inline-block w-[5px] h-[5px] rounded-full bg-outline-variant/50" />
            <span className="hud-label">GOOGLE</span>
          </div>
          <span className="text-data-mono text-outline-variant text-[9px]">[○ OFFLINE]</span>
          <button 
            onClick={handleConnect}
            className="hud-chip hud-chip--warning text-[8px] cursor-pointer hover:bg-warning/20"
          >
            CONNECT
          </button>
        </div>
      </div>
    );
  }

  const renderService = (name: string, active: boolean) => (
    <div className="flex items-center justify-between py-[5px]">
      <div className="flex items-center gap-1.5 min-w-[60px]">
        <span className={`inline-block w-[5px] h-[5px] rounded-full ${active ? "bg-primary" : "bg-outline-variant/50"}`} />
        <span className="hud-label uppercase">{name}</span>
      </div>
      <span className={`text-data-mono text-[9px] ${active ? "text-primary" : "text-outline-variant"}`}>
        [{active ? "● ACTIVE" : "○ OFFLINE"}]
      </span>
      {name === "GMAIL" && typeof status.email === "string" && (
        <span className="text-[9px] text-on-surface-variant max-w-[80px] truncate ml-2">
          {status.email as string}
        </span>
      )}
    </div>
  );

  return (
    <div className="shrink-0">
      <SectionHeader title="GOOGLE SERVICES" />
      <div className="flex flex-col divide-y divide-primary/[0.08]">
        {renderService("GMAIL", true)}
        {renderService("CALENDAR", true)}
        {renderService("DRIVE", true)}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   SECTION 5 — Research Pipeline
   ═══════════════════════════════════════════════════════════════ */
function ResearchPipelineControl() {
  const setOpen = useResearchStore((s) => s.setOpen);
  const taskState = useResearchStore((s) => s.taskState);

  return (
    <div className="shrink-0">
      <SectionHeader title="RESEARCH PIPELINE" />
      <div className="flex flex-col gap-2 mt-1">
        {taskState && (
          <div 
            className="flex flex-col gap-1.5 p-2 bg-primary/5 border border-primary/10 rounded-sm relative overflow-hidden"
            style={{
              background: "linear-gradient(180deg, rgba(76,215,246,0.02) 0%, rgba(76,215,246,0.06) 100%)",
            }}
          >
            {/* Top row: Topic and % */}
            <div className="flex items-center justify-between text-[9px]">
              <span 
                className="text-outline uppercase truncate max-w-[130px] font-bold"
                title={taskState.topic}
              >
                {taskState.topic}
              </span>
              <span className="text-primary font-bold font-mono">
                {Math.round(taskState.progress_percent)}%
              </span>
            </div>

            {/* Progress segment bar */}
            <div className="flex gap-[2px]">
              {Array.from({ length: 15 }, (_, i) => {
                const filled = Math.round((taskState.progress_percent / 100) * 15);
                const isActive = i < filled;
                return (
                  <div
                    key={i}
                    className="h-1.5 flex-1 transition-all duration-300"
                    style={{
                      background: isActive 
                        ? "linear-gradient(90deg, #4cd7f6, #06b6d4)" 
                        : "rgba(148, 163, 184, 0.15)",
                      boxShadow: isActive && i === filled - 1
                        ? "0 0 4px rgba(76, 215, 246, 0.6)" 
                        : "none",
                    }}
                  />
                );
              })}
            </div>

            {/* Bottom details row */}
            <div className="flex justify-between items-center text-[8px] font-mono text-on-surface-variant/80">
              <span className="uppercase tracking-wider">
                Stage: {taskState.stage.replace(/_/g, " ")}
              </span>
              <span 
                className={`uppercase font-bold tracking-widest ${
                  taskState.status === "running" 
                    ? "text-success animate-pulse" 
                    : taskState.status === "failed"
                      ? "text-error"
                      : "text-primary"
                }`}
              >
                {taskState.status}
              </span>
            </div>
          </div>
        )}
        <button
          onClick={() => setOpen(true)}
          className="hud-button w-full relative overflow-hidden group py-2"
          style={{
            borderColor: "rgba(76,215,246,0.35)",
            background: "linear-gradient(135deg, rgba(76,215,246,0.03) 0%, rgba(6,182,212,0.08) 100%)",
          }}
        >
          {/* Subtle moving shine overlay on hover */}
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-primary/15 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-1000 ease-out pointer-events-none" />
          
          <div className="flex items-center justify-center gap-1.5 text-[9px] tracking-widest font-bold font-mono">
            <span className="w-1.5 h-1.5 bg-primary rounded-full animate-pulse" style={{ boxShadow: "0 0 6px var(--color-glow-cyan-intense)" }} />
            LAUNCH CONTROL ROOM
          </div>
        </button>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   RIGHT PANEL — Main Export
   ═══════════════════════════════════════════════════════════════ */
const RightPanel = () => {
  return (
    <div 
      className="hud-panel hud-corner-bracket flex-1 flex flex-col min-h-0 !p-3 bg-surface-container overflow-y-auto" 
      style={{ 
        scrollbarWidth: "none",
        borderLeft: "1px solid rgba(76,215,246,0.12)",
        boxShadow: "inset 1px 0 12px rgba(76,215,246,0.03)",
      }}
    >
      {/* Extra corners (top-right + bottom-left) */}
      <span className="hud-corner-bracket--extra absolute inset-0 pointer-events-none" />

      {/* Section 1 — Proximity Radar (~35%) */}
      <ProximityRadar />

      {/* Divider */}
      <div className="my-2 h-px bg-primary/15 shrink-0" />

      {/* Section 2 — Objectives (~35%) */}
      <ActiveObjectives />

      {/* Divider */}
      <div className="my-2 h-px bg-primary/15 shrink-0" />

      {/* Section 3 — Voice Pipeline (~30%) */}
      <VoicePipeline />

      {/* Divider */}
      <div className="my-2 h-px bg-primary/15 shrink-0" />

      {/* Section 4 — Google Services */}
      <GoogleServices />

      {/* Divider */}
      <div className="my-2 h-px bg-primary/15 shrink-0" />

      {/* Section 5 — Research Pipeline */}
      <ResearchPipelineControl />
    </div>
  );
}

export default React.memo(RightPanel);
