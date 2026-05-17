import { type ReactNode } from "react";
import { useClock } from "@/hooks/useClock";
import { useUptime } from "@/hooks/useUptime";
import { useMetherStore } from "@/stores/metherStore";
import { WhatsAppPing } from "@/components/WhatsAppPing/WhatsAppPing";
import { ConfirmDialog } from "@/components/ConfirmDialog/ConfirmDialog";
import { TerminalFeed } from "@/components/TerminalFeed/TerminalFeed";

/* ═══════════════════════════════════════════════════════════════
   METHER OS — HUD Layout Shell
   Tactical HUD with 4 pinned edge zones + open center viewport.
   Now includes command bar zone above the bottom status bar.
   ═══════════════════════════════════════════════════════════════ */

/* ── Dimension constants ── */
const TOP_BAR_H = 40;       // px
const COMMAND_BAR_H = 48;   // px
const BOTTOM_BAR_H = 32;    // px
const BOTTOM_TOTAL = COMMAND_BAR_H + BOTTOM_BAR_H; // 80px
const SIDE_PANEL_W = 240;   // px

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
   Now reads connection status from Zustand store.
   ═══════════════════════════════════════════════════════════════ */
function TopBar() {
  const clock = useClock();
  const connectionStatus = useMetherStore((s) => s.connectionStatus);
  const voiceStatus = useMetherStore((s) => s.voiceStatus);

  /* Derive chip configs from connection status */
  const onlineChip =
    connectionStatus === "connected"
      ? { label: "● ONLINE", cls: "hud-chip hud-chip--success" }
      : connectionStatus === "connecting"
        ? { label: "○ CONNECTING", cls: "hud-chip !border-amber-500/50 !text-amber-400 !bg-amber-500/10 shadow-[0_0_10px_rgba(245,158,11,0.2)] motion-safe:animate-pulse" }
        : { label: "● OFFLINE", cls: "hud-chip !border-rose-500/50 !text-rose-400 !bg-rose-500/10" };

  return (
    <header
      id="hud-top-bar"
      className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-5
                 bg-surface-container border-b border-primary/20 select-none"
      style={{ height: TOP_BAR_H }}
    >
      {/* ── Left: System ID + status dots ── */}
      <div className="flex items-center gap-3">
        <div style={{ mixBlendMode: "screen" }} className="flex items-center h-[28px]">
          <img src="/logo.png" height={28} className="h-[28px] w-auto" alt="Logo" />
        </div>
        <div className="flex flex-col">
          <span className="font-space font-bold text-primary tracking-[0.08em] leading-tight">
            METHER OS
          </span>
          <span className="text-[10px] text-data-mono opacity-50 leading-tight">
            v1.0.0
          </span>
        </div>
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

      {/* ── Right: Status chips (reactive to connection) ── */}
      <div className="hidden md:flex items-center gap-2">
        <span className={onlineChip.cls}>{onlineChip.label}</span>
        {voiceStatus === "online" ? (
          <span className="hud-chip !border-[#c084fc]/50 !text-[#f3e8ff] !bg-[#c084fc]/10 shadow-[0_0_10px_rgba(192,132,252,0.2)]">
            ● VOICE
          </span>
        ) : (
          <span className="hud-chip opacity-50">○ VOICE</span>
        )}
        <span className="hud-chip">SECURE</span>
        <span className={`hud-chip ${connectionStatus === "connected" ? "hud-chip--success" : ""}`}>
          SYNC
        </span>
      </div>
    </header>
  );
}

/* ═══════════════════════════════════════════════════════════════
   BOTTOM BAR — Tool ID, tagline, uptime
   ═══════════════════════════════════════════════════════════════ */
function BottomBar() {
  const uptime = useUptime();
  const activeTool = useMetherStore((s) => s.activeTool);

  return (
    <footer
      id="hud-bottom-bar"
      className="fixed bottom-0 left-0 right-0 z-50 flex items-center justify-between px-5
                 bg-surface-container border-t border-primary/20 select-none"
      style={{ height: BOTTOM_BAR_H }}
    >
      {/* ── Left: Active tool name (from store) ── */}
      <div className="hidden md:flex items-center gap-2 min-w-[180px]">
        <span className="text-data-mono text-outline tracking-[0.08em]">&gt; TOOL:</span>
        <span className="text-data-mono text-on-surface-variant tracking-wider">
          {activeTool.toUpperCase()}
        </span>
      </div>

      {/* ── Center: Tagline ── */}
      <div className="absolute left-1/2 -translate-x-1/2 w-full text-center">
        <span className="text-data-mono text-outline-variant tracking-[0.12em] md:hidden">
          METHER OS
        </span>
        <span className="text-data-mono text-outline-variant tracking-[0.12em] hidden md:inline">
          METHER INTELLIGENCE OS // TACTICAL INTERFACE
        </span>
      </div>

      {/* ── Right: Uptime ── */}
      <div className="hidden md:flex items-center gap-2 min-w-[180px] justify-end">
        <span className="text-data-mono text-outline tracking-[0.08em]">UPTIME:</span>
        <span className="text-data-mono text-primary font-bold tracking-[0.15em]">
          {uptime} // IST
        </span>
        <span className="text-data-mono text-[10px] tracking-widest opacity-30 ml-4 hidden md:inline">
          OPEN SOURCE // MIT
        </span>
      </div>
    </footer>
  );
}

/* ═══════════════════════════════════════════════════════════════
   SIDE PANEL — Left / Right containers
   ═══════════════════════════════════════════════════════════════ */
function SidePanel({ side, children }: { side: "left" | "right"; children?: ReactNode }) {
  const posClass = side === "left" ? "left-0" : "right-0";

  return (
    <aside
      id={`hud-panel-${side}`}
      className={`fixed ${posClass} z-40 overflow-y-auto overflow-x-hidden hidden md:block`}
      style={{
        top: TOP_BAR_H,
        bottom: BOTTOM_TOTAL,
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
  const bars = [80, 65, 90, 70, 85];
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
        {bars.map((width, i) => (
          <div key={i} className="flex items-center gap-2">
            <span className="text-data-mono text-outline-variant">
              {String(i + 1).padStart(2, "0")}
            </span>
            <div
              className="h-[3px] bg-primary/10 flex-1"
              style={{ maxWidth: `${width}%` }}
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
      className="fixed z-30 flex items-center justify-center overflow-hidden left-0 right-0 md:left-[260px] md:right-[260px]"
      style={{
        top: TOP_BAR_H,
        bottom: BOTTOM_TOTAL,
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
   CommandInput is passed as a prop and rendered between
   the center viewport and the bottom bar.
   ═══════════════════════════════════════════════════════════════ */
interface HUDLayoutProps {
  children?: ReactNode;
  leftPanel?: ReactNode;
  rightPanel?: ReactNode;
  commandBar?: ReactNode;
}

export default function HUDLayout({
  children,
  leftPanel,
  rightPanel,
  commandBar,
}: HUDLayoutProps) {
  return (
    <div id="hud-layout" className="min-h-screen bg-void scan-line-overlay noise-overlay">
      {/* ── Full-screen vignette ── */}
      <div className="vignette-overlay" />
      {/* ── Edge bars ── */}
      <TopBar />
      <BottomBar />

      {/* ── Command bar (above bottom bar) ── */}
      {commandBar}

      {/* ── Side panels ── */}
      <SidePanel side="left">{leftPanel}</SidePanel>
      <SidePanel side="right">{rightPanel}</SidePanel>

      {/* ── Center viewport ── */}
      <CenterViewport>{children}</CenterViewport>

      <WhatsAppPing />
      <ConfirmDialog />
      <TerminalFeed />
    </div>
  );
}
