import type { ReactNode } from "react";
import { useClock } from "@/hooks/useClock";
import { useUptime } from "@/hooks/useUptime";

/* ═══════════════════════════════════════════════════════════════
   METHER OS — HUD Layout Shell
   Tactical HUD with 4 pinned edge zones + open center viewport.
   ═══════════════════════════════════════════════════════════════ */

/* ── Dimension constants ── */
const TOP_BAR_H = 40;   // px
const BOTTOM_BAR_H = 32; // px
const SIDE_PANEL_W = 240; // px

/* ── Status dot — blinking activity indicator ── */
function StatusDot({ color = "bg-success", delay = "0s" }: { color?: string; delay?: string }) {
  return (
    <span
      className={`inline-block w-[6px] h-[6px] rounded-full ${color}`}
      style={{
        animation: "breathe 3s ease-in-out infinite",
        animationDelay: delay,
      }}
    />
  );
}

/* ═══════════════════════════════════════════════════════════════
   TOP BAR — System identification & status
   ═══════════════════════════════════════════════════════════════ */
function TopBar() {
  const clock = useClock();

  return (
    <header
      id="hud-top-bar"
      className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-5
                 bg-surface-container border-b border-primary/20 select-none"
      style={{ height: TOP_BAR_H }}
    >
      {/* ── Left: System ID + status dots ── */}
      <div className="flex items-center gap-3">
        <span className="text-data-mono text-primary tracking-[0.15em] font-bold">
          METHER OS v1.0
        </span>
        <div className="flex items-center gap-1.5 ml-1">
          <StatusDot color="bg-success" delay="0s" />
          <StatusDot color="bg-primary" delay="0.5s" />
          <StatusDot color="bg-secondary" delay="1s" />
        </div>
      </div>

      {/* ── Center: Live clock ── */}
      <div className="absolute left-1/2 -translate-x-1/2 flex items-center gap-2">
        <span className="text-data-mono text-outline tracking-[0.08em]">SYS.TIME</span>
        <span className="text-label-caps text-primary text-glow-cyan tracking-[0.2em]">
          {clock}
        </span>
      </div>

      {/* ── Right: Status chips ── */}
      <div className="flex items-center gap-2">
        <span className="hud-chip hud-chip--success">ONLINE</span>
        <span className="hud-chip">SECURE</span>
        <span className="hud-chip">SYNC</span>
      </div>
    </header>
  );
}

/* ═══════════════════════════════════════════════════════════════
   BOTTOM BAR — Tool ID, tagline, uptime
   ═══════════════════════════════════════════════════════════════ */
function BottomBar() {
  const uptime = useUptime();

  return (
    <footer
      id="hud-bottom-bar"
      className="fixed bottom-0 left-0 right-0 z-50 flex items-center justify-between px-5
                 bg-surface-container border-t border-primary/20 select-none"
      style={{ height: BOTTOM_BAR_H }}
    >
      {/* ── Left: Active tool name ── */}
      <div className="flex items-center gap-2 min-w-[180px]">
        <span className="text-data-mono text-outline tracking-[0.08em]">&gt; TOOL:</span>
        <span className="text-data-mono text-on-surface-variant tracking-wider">
          STANDBY
        </span>
      </div>

      {/* ── Center: Tagline ── */}
      <div className="absolute left-1/2 -translate-x-1/2">
        <span className="text-data-mono text-outline-variant tracking-[0.12em]">
          METHER INTELLIGENCE OS // TACTICAL INTERFACE
        </span>
      </div>

      {/* ── Right: Uptime ── */}
      <div className="flex items-center gap-2 min-w-[180px] justify-end">
        <span className="text-data-mono text-outline tracking-[0.08em]">UPTIME</span>
        <span className="text-data-mono text-primary font-bold tracking-[0.15em]">
          {uptime}
        </span>
      </div>
    </footer>
  );
}

/* ═══════════════════════════════════════════════════════════════
   SIDE PANEL — Left / Right placeholder containers
   ═══════════════════════════════════════════════════════════════ */
function SidePanel({ side, children }: { side: "left" | "right"; children?: ReactNode }) {
  const posClass = side === "left" ? "left-0" : "right-0";

  return (
    <aside
      id={`hud-panel-${side}`}
      className={`fixed ${posClass} z-40 overflow-y-auto overflow-x-hidden`}
      style={{
        top: TOP_BAR_H,
        bottom: BOTTOM_BAR_H,
        width: SIDE_PANEL_W,
      }}
    >
      <div className="h-full p-3 flex flex-col gap-3">
        {children ?? <PanelPlaceholder label={`${side.toUpperCase()} PANEL`} />}
      </div>
    </aside>
  );
}

/* ── Placeholder panel with corner brackets ── */
function PanelPlaceholder({ label }: { label: string }) {
  return (
    <div className="hud-panel hud-corner-bracket flex-1 flex flex-col">
      {/* Extra corners (top-right + bottom-left) */}
      <span className="hud-corner-bracket--extra absolute inset-0 pointer-events-none" />

      {/* Header */}
      <div className="flex items-center gap-2 mb-3">
        <span className="w-1 h-3 bg-primary/50" />
        <span className="hud-label text-[10px]">{label}</span>
      </div>

      {/* Placeholder lines — simulated data readout */}
      <div className="flex-1 flex flex-col gap-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="flex items-center gap-2">
            <span className="text-data-mono text-outline-variant">
              {String(i + 1).padStart(2, "0")}
            </span>
            <div
              className="h-[3px] bg-primary/10 flex-1"
              style={{ maxWidth: `${60 + Math.random() * 40}%` }}
            />
          </div>
        ))}
      </div>

      {/* Footer label */}
      <div className="mt-auto pt-3 border-t border-primary/10">
        <span className="text-data-mono text-outline">:: AWAITING DATA</span>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   CENTER VIEWPORT — Grid background + children mount point
   ═══════════════════════════════════════════════════════════════ */
function CenterViewport({ children }: { children?: ReactNode }) {
  return (
    <main
      id="hud-center-viewport"
      className="fixed z-30 flex items-center justify-center overflow-hidden"
      style={{
        top: TOP_BAR_H,
        bottom: BOTTOM_BAR_H,
        left: SIDE_PANEL_W,
        right: SIDE_PANEL_W,
      }}
    >
      {/* Tactical grid background */}
      <div className="absolute inset-0 hud-grid" />

      {/* Radial vignette — focuses attention to center */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background:
            "radial-gradient(ellipse at center, transparent 30%, rgba(5, 8, 16, 0.6) 100%)",
        }}
      />

      {/* Crosshair guides — very subtle center indicators */}
      <div className="absolute inset-0 pointer-events-none flex items-center justify-center">
        {/* Horizontal line */}
        <div className="absolute w-full h-px bg-primary/[0.04]" />
        {/* Vertical line */}
        <div className="absolute h-full w-px bg-primary/[0.04]" />
        {/* Center tick marks */}
        <div className="absolute w-6 h-px bg-primary/20" />
        <div className="absolute h-6 w-px bg-primary/20" />
      </div>

      {/* Content mounts here (Voice Orb, etc.) */}
      <div className="relative z-10 flex items-center justify-center">
        {children}
      </div>
    </main>
  );
}

/* ═══════════════════════════════════════════════════════════════
   HUD LAYOUT — Main export
   Composes all edge zones around a central viewport.
   ═══════════════════════════════════════════════════════════════ */
interface HUDLayoutProps {
  children?: ReactNode;
  leftPanel?: ReactNode;
  rightPanel?: ReactNode;
  activeTool?: string;
}

export default function HUDLayout({
  children,
  leftPanel,
  rightPanel,
}: HUDLayoutProps) {
  return (
    <div id="hud-layout" className="min-h-screen bg-void scan-line-overlay noise-overlay">
      {/* ── Edge bars ── */}
      <TopBar />
      <BottomBar />

      {/* ── Side panels ── */}
      <SidePanel side="left">{leftPanel}</SidePanel>
      <SidePanel side="right">{rightPanel}</SidePanel>

      {/* ── Center viewport ── */}
      <CenterViewport>{children}</CenterViewport>
    </div>
  );
}
