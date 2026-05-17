import HUDLayout from "@/layouts/HUDLayout";
import { VoiceOrb } from "@/components/VoiceOrb";
import LeftPanel from "@/components/panels/LeftPanel";
import { useOrbState } from "@/hooks/useOrbState";

/**
 * METHER OS — Root Application Shell
 *
 * Wraps the HUD layout and renders the Voice Orb in the center viewport.
 * The orb auto-cycles through states in demo mode; click to toggle manually.
 */
function App() {
  const { state, toggle } = useOrbState(true);

  return (
    <HUDLayout leftPanel={<LeftPanel />}>
      <VoiceOrb state={state} onActivate={toggle} />
    </HUDLayout>
  );
}

export default App;
