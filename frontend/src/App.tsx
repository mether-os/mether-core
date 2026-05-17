import "./index.css";

/**
 * METHER OS — Root Application Shell
 *
 * This is the entry point for the tactical HUD interface.
 * All panel layouts, routing, and global overlays will mount here.
 */
function App() {
  return (
    <div
      id="mether-root"
      className="relative min-h-screen bg-void hud-grid scan-line-overlay noise-overlay"
    >
      {/* System status bar will go here */}

      {/* Main viewport — panels mount inside */}
      <main className="relative z-10 flex items-center justify-center min-h-screen">
        <div className="text-center space-y-4 animate-fade-in">
          {/* Boot identifier */}
          <p className="hud-label tracking-[0.25em] text-on-surface-variant">
            :: SYSTEM INIT
          </p>

          {/* Wordmark */}
          <h1 className="text-headline-xl text-primary text-glow-cyan">
            METHER OS
          </h1>

          {/* Status */}
          <p className="text-data-mono text-outline">
            v0.1.0 &middot; TACTICAL INTELLIGENCE INTERFACE &middot; STANDBY
          </p>

          {/* Boot chip */}
          <div className="flex justify-center pt-2">
            <span className="hud-chip hud-chip--success">ONLINE</span>
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
