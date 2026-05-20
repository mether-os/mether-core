import React, { useCallback } from "react";
import HUDLayout from "@/layouts/HUDLayout";
import METHERCore from "@/components/METHERCore/METHERCore";
import { CommandInput } from "@/components/CommandInput";
import { ResponseDisplay } from "@/components/ResponseDisplay";
import LeftPanel, { AgentLog } from "@/components/panels/LeftPanel";
import RightPanel from "@/components/panels/RightPanel";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useMetherStore } from "@/stores/metherStore";
import { useOrbCycle } from "@/hooks/useOrbCycle";

class ErrorBoundary extends React.Component<{children: React.ReactNode}, {hasError: boolean, error: Error | null}> {
  constructor(props: {children: React.ReactNode}) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-void text-error font-mono flex flex-col items-center justify-center p-6 text-center">
          <h1 className="text-xl font-bold tracking-widest mb-4">:: SYSTEM ERROR // CORE EXCEPTION DETECTED</h1>
          <div className="bg-error/10 border border-error/30 p-4 max-w-2xl text-left text-sm whitespace-pre-wrap mb-6">
            {this.state.error?.message}
          </div>
          <button 
            onClick={() => window.location.reload()}
            className="border border-error/50 hover:bg-error/20 px-6 py-2 tracking-widest transition-colors"
          >
            [RESTART]
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

/**
 * METHER OS — Root Application Shell
 *
 * Wires together:
 * • HUDLayout (top/bottom bars, side panels, center viewport)
 * • VoiceOrb (reads orbState from store)
 * • CommandInput → WebSocket → Agent Log
 * • ResponseDisplay (AI responses)
 * • Demo mode auto-cycling for orb states
 */
function App() {
  const { send, isConnected } = useWebSocket();

  const orbState = useMetherStore((s) => s.orbState);
  const setOrbState = useMetherStore((s) => s.setOrbState);
  const isDemo = useMetherStore((s) => s.isDemo);
  const setDemo = useMetherStore((s) => s.setDemo);
  const voiceStatus = useMetherStore((s) => s.voiceStatus);
  const addLog = useMetherStore((s) => s.addLog);
  const addCommand = useMetherStore((s) => s.addCommand);
  const commandHistory = useMetherStore((s) => s.commandHistory);
  const incrementStat = useMetherStore((s) => s.incrementStat);

  /* ── Demo mode: auto-cycle orb states ── */
  useOrbCycle();

  /* ── Orb click → toggle listen ── */
  const handleOrbActivate = useCallback(() => {
    setDemo(false);
    setOrbState(orbState === "idle" ? "listening" : "idle");
  }, [orbState, setOrbState, setDemo]);

  /* ── Command submit ── */
  const handleCommand = useCallback(
    (command: string) => {
      setDemo(false);
      addCommand(command);
      addLog("CMD", `> ${command}`);
      incrementStat("commands");

      // Send over WebSocket (will log locally if offline)
      send(command);
    },
    [send, addCommand, addLog, incrementStat, setDemo]
  );

  return (
    <HUDLayout
      leftPanel={<LeftPanel />}
      rightPanel={<RightPanel />}
      commandBar={
        <>
          <ResponseDisplay />
          <CommandInput
            onSubmit={handleCommand}
            commandHistory={commandHistory}
            isConnected={isConnected}
          />
        </>
      }
    >
      <div className="flex flex-col items-center justify-center w-full h-full">
        <METHERCore 
          state={(voiceStatus === "offline" && !isDemo && orbState === "idle") ? "sleeping" : orbState} 
          onActivate={handleOrbActivate} 
        />
        <div className="md:hidden mt-8 w-[90%] max-w-sm h-32 border border-primary/20 bg-surface-container/50 rounded-sm p-2 flex flex-col pointer-events-auto">
          <AgentLog />
        </div>
      </div>
    </HUDLayout>
  );
}

export default function AppWrapper() {
  return (
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  );
}
