import { useState, useEffect, useRef, useMemo } from "react";
import { useMetherStore } from "@/stores/metherStore";

/* ═══════════════════════════════════════════════════════════════
   METHER OS — Right Panel
   Proximity Radar (35%) + Objectives (35%) + Session Stats (30%)
   ═══════════════════════════════════════════════════════════════ */

/* ── Constants ── */
const SEGMENT_COUNT = 10;
const RADAR_SIZE = 180;
const RADAR_CENTER = RADAR_SIZE / 2;
const SWEEP_DURATION = 3; // seconds per full rotation

/* ── Helpers ── */
function randomInRange(min: number, max: number): number {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

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
      {Array.from({ length: SEGMENT_COUNT }, (_, i) => (
        <div
          key={i}
          className={`w-[5px] h-[5px] transition-colors duration-300 ${
            i < filled ? "bg-primary/70" : "bg-outline-variant/20"
          }`}
        />
      ))}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   SECTION 1 — Proximity Radar (SVG)
   ═══════════════════════════════════════════════════════════════ */

interface Blip {
  id: number;
  angle: number; // degrees
  radius: number; // 0–1 normalized
  speed: number; // deg/s drift
}

function ProximityRadar() {
  const [sweepAngle, setSweepAngle] = useState(0);
  const animRef = useRef<number>(0);
  const lastTime = useRef<number>(0);

  /* ── Generate blips once ── */
  const blips = useMemo<Blip[]>(() => {
    return Array.from({ length: 5 }, (_, i) => ({
      id: i,
      angle: Math.random() * 360,
      radius: 0.25 + Math.random() * 0.6,
      speed: 0.3 + Math.random() * 0.8,
    }));
  }, []);

  /* ── Blip drift state ── */
  const [blipAngles, setBlipAngles] = useState(() => blips.map((b) => b.angle));

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
              <stop offset="100%" stopColor="rgba(76, 215, 246, 0.25)" />
            </linearGradient>

            {/* Blip glow filter */}
            <filter id="blipGlow">
              <feGaussianBlur stdDeviation="2" result="blur" />
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
          <circle
            cx={RADAR_CENTER}
            cy={RADAR_CENTER}
            r="2.5"
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

            return (
              <circle
                key={blip.id}
                cx={bx}
                cy={by}
                r="2.5"
                fill={`rgba(76, 215, 246, ${brightness})`}
                filter={brightness > 0.5 ? "url(#blipGlow)" : undefined}
              />
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

const OBJECTIVES: Objective[] = [
  { name: "BUILD METHER CORE", progress: 15, status: "IN PROGRESS" },
  { name: "CONNECT VOICE PIPELINE", progress: 0, status: "PENDING" },
  { name: "WHATSAPP BRIDGE", progress: 0, status: "PENDING" },
];

function ObjectiveItem({ obj }: { obj: Objective }) {
  const chipClass =
    obj.status === "IN PROGRESS"
      ? "hud-chip"
      : obj.status === "COMPLETE"
        ? "hud-chip hud-chip--success"
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
  return (
    <div className="shrink-0">
      <SectionHeader title="OBJECTIVES" />
      <div className="flex flex-col divide-y divide-primary/[0.08]">
        {OBJECTIVES.map((obj) => (
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
  );
}

/* ═══════════════════════════════════════════════════════════════
   RIGHT PANEL — Main Export
   ═══════════════════════════════════════════════════════════════ */
export default function RightPanel() {
  return (
    <div className="hud-panel hud-corner-bracket flex-1 flex flex-col min-h-0 !p-3 bg-surface-container">
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
    </div>
  );
}
