import { motion, type Variants } from "framer-motion";
import { useMemo, useState, useCallback } from "react";

/* ═══════════════════════════════════════════════════════════════
   METHER OS — Voice Orb
   The central intelligence core of the tactical HUD.

   4 states: idle · listening · processing · speaking
   6 concentric layers rendered inside-out via absolute positioning.
   Click: triggers a pulse ring effect.
   ═══════════════════════════════════════════════════════════════ */

export type OrbState = "idle" | "listening" | "processing" | "speaking";

export interface VoiceOrbProps {
  state: OrbState;
  onActivate?: () => void;
}

/* ── Per-state config ── */
const STATE_CONFIG = {
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
  },
  listening: {
    label: "LISTENING",
    coreScale: 1.15,
    coreOpacity: 0.9,
    glowOpacity: 0.5,
    glowScale: 1.3,
    glowBlur: 50,
    ringSpeed: 1.8,
    pulseSpeed: 1.5,
    showWaveform: true,
    flickerCore: false,
  },
  processing: {
    label: "PROCESSING",
    coreScale: 1.05,
    coreOpacity: 0.7,
    glowOpacity: 0.35,
    glowScale: 1.1,
    glowBlur: 40,
    ringSpeed: 2.5,
    pulseSpeed: 2,
    showWaveform: false,
    flickerCore: false,
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
    showWaveform: false,
    flickerCore: true,
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
}: {
  opacity: number;
  scale: number;
  blur: number;
  pulseSpeed: number;
}) {
  return (
    <motion.div
      className="absolute rounded-full"
      style={{
        width: GLOW_RING_SIZE,
        height: GLOW_RING_SIZE,
        background:
          "radial-gradient(circle, rgba(76, 215, 246, 0.4) 0%, rgba(76, 215, 246, 0.08) 60%, transparent 100%)",
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
}: {
  scale: number;
  opacity: number;
  flicker: boolean;
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
          "radial-gradient(circle, rgba(76, 215, 246, 0.95) 0%, rgba(76, 215, 246, 0.3) 50%, transparent 100%)",
        boxShadow: `
          0 0 20px rgba(76, 215, 246, ${opacity * 0.4}),
          0 0 40px rgba(76, 215, 246, ${opacity * 0.2}),
          0 0 80px rgba(76, 215, 246, ${opacity * 0.1})
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

/* ── Waveform bars (visible only in listening state) ── */
function WaveformBars({ visible }: { visible: boolean }) {
  const bars = useMemo(
    () =>
      Array.from({ length: 8 }, (_, i) => ({
        id: i,
        delay: i * 0.08,
        baseHeight: 12 + Math.random() * 8,
      })),
    []
  );

  return (
    <motion.div
      className="absolute flex items-center gap-[3px]"
      style={{ bottom: -40 }}
      animate={{ opacity: visible ? 1 : 0 }}
      transition={{ duration: 0.3 }}
    >
      {bars.map((bar) => (
        <motion.div
          key={bar.id}
          className="rounded-sm"
          style={{
            width: 3,
            background:
              "linear-gradient(to top, rgba(76, 215, 246, 0.9), rgba(173, 198, 255, 0.6))",
          }}
          animate={
            visible
              ? {
                  height: [
                    bar.baseHeight,
                    bar.baseHeight * 2.5,
                    bar.baseHeight * 0.8,
                    bar.baseHeight * 1.8,
                    bar.baseHeight,
                  ],
                }
              : { height: 2 }
          }
          transition={
            visible
              ? {
                  duration: 0.6 + Math.random() * 0.4,
                  repeat: Infinity,
                  ease: "easeInOut",
                  delay: bar.delay,
                }
              : { duration: 0.3 }
          }
        />
      ))}
    </motion.div>
  );
}

/* ── State label text ── */
function StateLabel({ label }: { label: string }) {
  return (
    <motion.span
      key={label}
      className="absolute text-data-mono text-primary tracking-[0.2em] font-bold select-none pointer-events-none"
      style={{ bottom: -65 }}
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -6 }}
      transition={{ duration: 0.3 }}
    >
      {`:: ${label}`}
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

      {/* Layer 1 — Outer decorative ring */}
      <OuterRing speed={cfg.ringSpeed} />

      {/* Layer 2 — Middle ring */}
      <MiddleRing speed={cfg.ringSpeed} />

      {/* Layer 3 — Tick ring */}
      <TickRing speed={cfg.ringSpeed} />

      {/* Layer 4 — Glow ring */}
      <GlowRing
        opacity={cfg.glowOpacity}
        scale={cfg.glowScale}
        blur={cfg.glowBlur}
        pulseSpeed={cfg.pulseSpeed}
      />

      {/* Layer 5 — Core */}
      <Core
        scale={cfg.coreScale}
        opacity={cfg.coreOpacity}
        flicker={cfg.flickerCore}
      />

      {/* Waveform bars (listening only) */}
      <WaveformBars visible={cfg.showWaveform} />

      {/* State label */}
      <StateLabel label={cfg.label} />
    </motion.div>
  );
}

