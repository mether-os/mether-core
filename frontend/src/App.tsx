import { useEffect, useCallback } from "react";
import HUDLayout from "@/layouts/HUDLayout";
import { VoiceOrb } from "@/components/VoiceOrb";
import { CommandInput } from "@/components/CommandInput";
import { AIResponseStreamer } from "@/components/AIResponseStreamer";
import LeftPanel from "@/components/panels/LeftPanel";
import RightPanel from "@/components/panels/RightPanel";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useMetherStore } from "@/stores/metherStore";
import type { OrbState } from "@/stores/metherStore";

/**
 * METHER OS — Root Application Shell
 *
 * Wires together:
 * • HUDLayout (top/bottom bars, side panels, center viewport)
 * • VoiceOrb (reads orbState from store)
 * • CommandInput → WebSocket → Agent Log
 * • AIResponseStreamer (demo mode typewriter AI responses)
 * • Demo mode auto-cycling for orb states
 */
function App() {
  const { send, isConnected } = useWebSocket();

  const orbState = useMetherStore((s) => s.orbState);
  const setOrbState = useMetherStore((s) => s.setOrbState);
  const isDemo = useMetherStore((s) => s.isDemo);
  const setDemo = useMetherStore((s) => s.setDemo);
  const addLog = useMetherStore((s) => s.addLog);
  const addCommand = useMetherStore((s) => s.addCommand);
  const commandHistory = useMetherStore((s) => s.commandHistory);
  const incrementStat = useMetherStore((s) => s.incrementStat);

  /* ── Demo mode: auto-cycle orb states ── */
  useEffect(() => {
    if (!isDemo) return;

    const sequence: OrbState[] = ["idle", "listening", "processing", "speaking"];
    let idx = 0;
    setOrbState(sequence[idx]);

    const id = setInterval(() => {
      idx = (idx + 1) % sequence.length;
      setOrbState(sequence[idx]);
    }, 4000);

    return () => clearInterval(id);
  }, [isDemo, setOrbState]);

  /* ── Orb click → toggle listen ── */
  const handleOrbActivate = useCallback(() => {
    setDemo(false);
    setOrbState(orbState === "idle" ? "listening" : "idle");
  }, [orbState, setOrbState, setDemo]);

  /* ── Command submit ── */
  const handleCommand = useCallback(
    (command: string) => {
      addCommand(command);
      addLog("CMD", `> ${command}`);
      incrementStat("commands");

      // Send over WebSocket (will log locally if offline)
      send(command);
    },
    [send, addCommand, addLog, incrementStat]
  );

  return (
    <HUDLayout
      leftPanel={<LeftPanel />}
      rightPanel={<RightPanel />}
      commandBar={
        <>
          <AIResponseStreamer />
          <CommandInput
            onSubmit={handleCommand}
            commandHistory={commandHistory}
            isConnected={isConnected}
          />
        </>
      }
    >
      <VoiceOrb state={orbState} onActivate={handleOrbActivate} />
    </HUDLayout>
  );
}

export default App;
