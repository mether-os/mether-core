import HUDLayout from "@/layouts/HUDLayout";

/**
 * METHER OS — Root Application Shell
 *
 * Wraps the HUD layout and renders the central viewport content.
 * Voice Orb, modal overlays, and route content will mount here.
 */
function App() {
  return (
    <HUDLayout>
      {/* Center placeholder — Voice Orb will mount here */}
      <div className="flex flex-col items-center gap-4 animate-fade-in select-none">
        {/* Orb placeholder ring */}
        <div className="relative flex items-center justify-center">
          {/* Outer ring */}
          <div
            className="absolute w-40 h-40 rounded-full border border-primary/20 animate-ring-spin"
            style={{ borderStyle: "dashed" }}
          />
          {/* Middle ring */}
          <div
            className="absolute w-28 h-28 rounded-full border border-primary/15 animate-ring-spin-reverse"
            style={{ borderStyle: "dashed" }}
          />
          {/* Inner core glow */}
          <div className="w-16 h-16 rounded-full bg-primary/10 animate-breathe flex items-center justify-center">
            <div className="w-6 h-6 rounded-full bg-primary/30 animate-pulse-glow" />
          </div>
        </div>

        {/* Status text */}
        <p className="hud-label tracking-[0.25em] text-on-surface-variant mt-2">
          :: VOICE ORB STANDBY
        </p>
        <p className="text-data-mono text-outline">
          AWAITING ACTIVATION
        </p>
      </div>
    </HUDLayout>
  );
}

export default App;
