import { motion, type Variants } from "framer-motion";
import { useState, useCallback } from "react";

/* ═══════════════════════════════════════════════════════════════
   METHER OS — Voice Orb
   The central intelligence core of the tactical HUD.

   4 states: idle · listening · processing · speaking
   6 concentric layers rendered inside-out via absolute positioning.
   Click: triggers a pulse ring effect.
   ═══════════════════════════════════════════════════════════════ */

export type OrbState = "sleeping" | "idle" | "listening" | "processing" | "speaking";

export interface VoiceOrbProps {
  state: OrbState;
  onActivate?: () => void;
}

/* ── Per-state config ── */
const STATE_CONFIG = {
  sleeping: {
    label: "OFFLINE",
    coreScale: 0.9,
    coreOpacity: 0.1,
    glowOpacity: 0.05,
    glowScale: 0.9,
    glowBlur: 10,
    ringSpeed: 5,
    pulseSpeed: 8,
    showWaveform: false,
    flickerCore: false,
    ringOpacity: 0.2,
  },
  idle: {
    label: "STANDBY",
    coreScale: 1,
    coreOpacity: 0.35,
    glowOpacity: 0.15,
    glowScale: 1,
    glowBlur: 30,
    ringSpeed: 1,
    pulseSpeed: 4,
    showWaveform: false,
    flickerCore: false,
    ringOpacity: 1,
  },
  listening: {
    label: "LISTENING",
    coreScale: 1.15,
    coreOpacity: 0.9,
    glowOpacity: 0.5,
    glowScale: 1.3,
    glowBlur: 50,
    ringSpeed: 3,
    pulseSpeed: 1.5,
    showWaveform: true,
    flickerCore: false,
    ringOpacity: 1,
  },
  processing: {
    label: "PROCESSING",
    coreScale: 1.05,
    coreOpacity: 0.7,
    glowOpacity: 0.35,
    glowScale: 1.1,
    glowBlur: 40,
    ringSpeed: 1.5,
    pulseSpeed: 2,
    showWaveform: false,
    flickerCore: false,
    ringOpacity: 1,
  },
  speaking: {
    label: "SPEAKING",
    coreScale: 1.2,
    coreOpacity: 1,
    glowOpacity: 0.65,
    glowScale: 1.4,
    glowBlur: 60,
    ringSpeed: 2,
    pulseSpeed: 0.8,
    showWaveform: true, // speaking shows taller frequency bars
    flickerCore: true,
    ringOpacity: 1,
  },
} as const;

/* ── Shared spring ── */
const SPRING = { type: "spring" as const, stiffness: 120, damping: 18 };

/* ── Size constants ── */
const ORB_SIZE = 280;
const CORE_SIZE = 56;
const GLOW_RING_SIZE = 100;
const RING_3_SIZE = 150;
const RING_2_SIZE = 200;
const RING_1_SIZE = 260;

/* ═══════════════════════════════════════════════════════════════
   SUB-COMPONENTS
   ═══════════════════════════════════════════════════════════════ */

/* ── Layer 1: Outer decorative ring (dashed, clockwise) ── */
function OuterRing({ speed }: { speed: number }) {
  return (
    <motion.div
      className="absolute rounded-full"
      style={{
        width: RING_1_SIZE,
        height: RING_1_SIZE,
        border: "1px dashed rgba(76, 215, 246, 0.3)",
      }}
      animate={{ rotate: 360 }}
      transition={{ duration: 20 / speed, repeat: Infinity, ease: "linear" }}
    />
  );
}

/* ── Layer 2: Second ring (dashed, counter-clockwise, larger dashes) ── */
function MiddleRing({ speed }: { speed: number }) {
  return (
    <motion.div
      className="absolute rounded-full"
      style={{
        width: RING_2_SIZE,
        height: RING_2_SIZE,
        border: "1.5px dashed rgba(76, 215, 246, 0.5)",
        strokeDasharray: "12 8",
      }}
      animate={{ rotate: -360 }}
      transition={{ duration: 14 / speed, repeat: Infinity, ease: "linear" }}
    />
  );
}

/* ── Layer 3: Solid thin ring with 4 cardinal tick marks ── */
function TickRing({ speed }: { speed: number }) {
  return (
    <motion.div
      className="absolute rounded-full"
      style={{ width: RING_3_SIZE, height: RING_3_SIZE }}
      animate={{ rotate: 360 }}
      transition={{ duration: 30 / speed, repeat: Infinity, ease: "linear" }}
    >
      {/* Circle */}
      <div
        className="absolute inset-0 rounded-full"
        style={{ border: "1px solid rgba(76, 215, 246, 0.25)" }}
      />
      {/* 4 tick marks at 0° / 90° / 180° / 270° */}
      {[0, 90, 180, 270].map((deg) => (
        <div
          key={deg}
          className="absolute"
          style={{
            width: 2,
            height: 10,
            background: "rgba(76, 215, 246, 0.6)",
            top: "50%",
            left: "50%",
            transformOrigin: `0 ${RING_3_SIZE / 2}px`,
            transform: `rotate(${deg}deg) translate(-1px, -${RING_3_SIZE / 2}px)`,
          }}
        />
      ))}
    </motion.div>
  );
}

/* ── Layer 4: Inner glow ring (pulsing) ── */
function GlowRing({
  opacity,
  scale,
  blur,
  pulseSpeed,
  color = "rgba(76, 215, 246, 0.4)",
  fadeColor = "rgba(76, 215, 246, 0.08)",
}: {
  opacity: number;
  scale: number;
  blur: number;
  pulseSpeed: number;
  color?: string;
  fadeColor?: string;
}) {
  return (
    <motion.div
      className="absolute rounded-full"
      style={{
        width: GLOW_RING_SIZE,
        height: GLOW_RING_SIZE,
        background:
          `radial-gradient(circle, ${color} 0%, ${fadeColor} 60%, transparent 100%)`,
        filter: `blur(${blur}px)`,
      }}
      animate={{
        opacity: [opacity * 0.7, opacity, opacity * 0.7],
        scale: [scale * 0.95, scale, scale * 0.95],
      }}
      transition={{
        duration: pulseSpeed,
        repeat: Infinity,
        ease: "easeInOut",
      }}
    />
  );
}

/* ── Layer 5: Core ── */
function Core({
  scale,
  opacity,
  flicker,
  color = "rgba(76, 215, 246, 0.95)",
  glowBase = "rgba(76, 215, 246,",
}: {
  scale: number;
  opacity: number;
  flicker: boolean;
  color?: string;
  glowBase?: string;
}) {
  const flickerVariants: Variants = flicker
    ? {
        animate: {
          opacity: [opacity, opacity * 0.6, opacity, opacity * 0.75, opacity],
          scale: [scale, scale * 0.95, scale * 1.02, scale * 0.97, scale],
        },
      }
    : {
        animate: {
          opacity: opacity,
          scale: scale,
        },
      };

  return (
    <motion.div
      className="absolute rounded-full"
      style={{
        width: CORE_SIZE,
        height: CORE_SIZE,
        background:
          `radial-gradient(circle, ${color} 0%, ${glowBase} 0.3) 50%, transparent 100%)`,
        boxShadow: `
          0 0 20px ${glowBase} ${opacity * 0.4}),
          0 0 40px ${glowBase} ${opacity * 0.2}),
          0 0 80px ${glowBase} ${opacity * 0.1})
        `,
      }}
      variants={flickerVariants}
      animate="animate"
      transition={
        flicker
          ? { duration: 0.6, repeat: Infinity, ease: "easeInOut" }
          : { ...SPRING }
      }
    />
  );
}

/* ── Waveform bars (listening/speaking state) ── */
const WAVEFORM_BARS = [
  { id: 0, delay: 0, baseHeight: 14 },
  { id: 1, delay: 0.08, baseHeight: 18 },
  { id: 2, delay: 0.16, baseHeight: 13 },
  { id: 3, delay: 0.24, baseHeight: 19 },
  { id: 4, delay: 0.32, baseHeight: 15 },
  { id: 5, delay: 0.40, baseHeight: 17 },
  { id: 6, delay: 0.48, baseHeight: 12 },
  { id: 7, delay: 0.56, baseHeight: 16 },
];

const WAVEFORM_DURATIONS_SPEAKING = [0.35, 0.42, 0.38, 0.48, 0.33, 0.45, 0.37, 0.41];
const WAVEFORM_DURATIONS_LISTENING = [0.72, 0.85, 0.68, 0.92, 0.75, 0.88, 0.70, 0.80];

function WaveformBars({ visible, isSpeaking }: { visible: boolean; isSpeaking?: boolean }) {
  const bars = WAVEFORM_BARS;

  return (
    <motion.div
      className="absolute flex items-center gap-[3px]"
      style={{ bottom: -40 }}
      animate={{ opacity: visible ? 1 : 0 }}
      transition={{ duration: 0.3 }}
    >
      {bars.map((bar) => {
        const h = isSpeaking ? bar.baseHeight * 1.5 : bar.baseHeight;
        return (
          <motion.div
            key={bar.id}
            className="rounded-sm"
            style={{
              width: isSpeaking ? 4 : 3,
              background: isSpeaking 
                ? "linear-gradient(to top, rgba(76, 215, 246, 1), rgba(173, 198, 255, 0.8))"
                : "linear-gradient(to top, rgba(76, 215, 246, 0.9), rgba(173, 198, 255, 0.6))",
            }}
            animate={
              visible
                ? {
                    height: [
                      h,
                      h * (isSpeaking ? 3.5 : 2.5),
                      h * 0.8,
                      h * (isSpeaking ? 2.5 : 1.8),
                      h,
                    ],
                  }
                : { height: 2 }
            }
            transition={
              visible
                ? {
                    duration: isSpeaking ? WAVEFORM_DURATIONS_SPEAKING[bar.id] : WAVEFORM_DURATIONS_LISTENING[bar.id],
                    repeat: Infinity,
                    ease: "easeInOut",
                    delay: bar.delay,
                  }
                : { duration: 0.3 }
            }
          />
        );
      })}
    </motion.div>
  );
}

/* ── State label text ── */
function StateLabel({ label, isProcessing }: { label: string; isProcessing?: boolean }) {
  return (
    <motion.span
      key={label}
      className="absolute text-data-mono text-primary tracking-[0.2em] font-bold select-none pointer-events-none flex items-center"
      style={{ bottom: -65 }}
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -6 }}
      transition={{ duration: 0.3 }}
    >
      {`:: ${label}`}
      {isProcessing && (
        <motion.span
          animate={{ opacity: [0, 1, 0] }}
          transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
        >
          ...
        </motion.span>
      )}
    </motion.span>
  );
}

/* ═══════════════════════════════════════════════════════════════
   VOICE ORB — Main Export
   ═══════════════════════════════════════════════════════════════ */

export default function VoiceOrb({ state, onActivate }: VoiceOrbProps) {
  const cfg = STATE_CONFIG[state];
  const [pulseKey, setPulseKey] = useState(0);

  const handleClick = useCallback(() => {
    setPulseKey((k) => k + 1);
    onActivate?.();
  }, [onActivate]);

  return (
    <motion.div
      className="relative flex items-center justify-center cursor-pointer select-none"
      style={{ width: ORB_SIZE, height: ORB_SIZE }}
      onClick={handleClick}
      whileHover={{ scale: 1.03 }}
      whileTap={{ scale: 0.95 }}
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={SPRING}
    >
      {/* ── Click pulse ring ── */}
      <div
        key={pulseKey}
        className={`absolute rounded-full pointer-events-none ${
          pulseKey > 0 ? "orb-click-pulse" : ""
        }`}
        style={{ width: CORE_SIZE, height: CORE_SIZE }}
      />

      {/* ── Ambient background glow ── */}
      <motion.div
        className="absolute rounded-full pointer-events-none"
        style={{
          width: ORB_SIZE * 1.2,
          height: ORB_SIZE * 1.2,
          background:
            "radial-gradient(circle, rgba(76, 215, 246, 0.06) 0%, transparent 70%)",
        }}
        animate={{
          opacity: [cfg.glowOpacity * 0.5, cfg.glowOpacity, cfg.glowOpacity * 0.5],
          scale: [0.95, 1.05, 0.95],
        }}
        transition={{ duration: cfg.pulseSpeed * 1.5, repeat: Infinity, ease: "easeInOut" }}
      />

      {/* ── Listening pulse ring ── */}
      {state === "listening" && (
        <motion.div
          className="absolute rounded-full border border-primary/40 pointer-events-none"
          style={{ width: CORE_SIZE, height: CORE_SIZE }}
          animate={{ scale: [1, 2.5], opacity: [0.8, 0] }}
          transition={{ duration: 1.5, repeat: Infinity, ease: "easeOut" }}
        />
      )}

      {/* Layer 1-3 wrapped for ringOpacity */}
      <motion.div 
        className="absolute inset-0 flex items-center justify-center pointer-events-none"
        animate={{ opacity: cfg.ringOpacity }}
        transition={{ duration: 0.5 }}
      >
        <OuterRing speed={cfg.ringSpeed} />
        <MiddleRing speed={cfg.ringSpeed} />
        <TickRing speed={cfg.ringSpeed} />
      </motion.div>

      {/* Layer 4 — Glow ring */}
      <GlowRing
        opacity={cfg.glowOpacity}
        scale={cfg.glowScale}
        blur={cfg.glowBlur}
        pulseSpeed={cfg.pulseSpeed}
        color={state === "processing" ? "rgba(245, 158, 11, 0.4)" : undefined}
        fadeColor={state === "processing" ? "rgba(245, 158, 11, 0.08)" : undefined}
      />

      {/* Layer 5 — Core */}
      <Core
        scale={cfg.coreScale}
        opacity={cfg.coreOpacity}
        flicker={cfg.flickerCore}
        color={state === "processing" ? "rgba(251, 191, 36, 0.95)" : undefined}
        glowBase={state === "processing" ? "rgba(245, 158, 11," : undefined}
      />

      {/* Waveform bars */}
      <WaveformBars visible={cfg.showWaveform} isSpeaking={state === "speaking"} />

      {/* State label */}
      <StateLabel label={cfg.label} isProcessing={state === "processing"} />
    </motion.div>
  );
}

