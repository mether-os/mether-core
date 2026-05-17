import HUDLayout from "@/layouts/HUDLayout";
import { VoiceOrb } from "@/components/VoiceOrb";
import LeftPanel from "@/components/panels/LeftPanel";
import RightPanel from "@/components/panels/RightPanel";
import { useOrbState } from "@/hooks/useOrbState";

/**
 * METHER OS — Root Application Shell
 *
 * Wraps the HUD layout and renders the Voice Orb in the center viewport.
 * Left panel: System Vitals + Agent Log
 * Right panel: Proximity Radar + Objectives + Session Stats
 */
function App() {
  const { state, toggle } = useOrbState(true);

  return (
    <HUDLayout leftPanel={<LeftPanel />} rightPanel={<RightPanel />}>
      <VoiceOrb state={state} onActivate={toggle} />
    </HUDLayout>
  );
}

export default App;
