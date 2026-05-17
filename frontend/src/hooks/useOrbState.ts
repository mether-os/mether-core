import { useState, useEffect, useCallback } from "react";

/* ── Orb state types ── */
export type OrbState = "idle" | "listening" | "processing" | "speaking";

interface UseOrbStateReturn {
  state: OrbState;
  setState: (s: OrbState) => void;
  toggle: () => void;
  isDemo: boolean;
  setDemo: (on: boolean) => void;
}

/**
 * Orb state manager.
 *
 * • `toggle()` — quick idle↔listening switch (click handler)
 * • `setDemo(true)` — auto-cycles: idle → listening → processing → speaking → idle (4 s each)
 */
export function useOrbState(initialDemo = true): UseOrbStateReturn {
  const [state, setState] = useState<OrbState>("idle");
  const [isDemo, setDemo] = useState(initialDemo);

  /* ── Demo auto-cycle ── */
  useEffect(() => {
    if (!isDemo) return;

    const sequence: OrbState[] = ["idle", "listening", "processing", "speaking"];
    let idx = 0;

    setState(sequence[idx]);

    const id = setInterval(() => {
      idx = (idx + 1) % sequence.length;
      setState(sequence[idx]);
    }, 4000);

    return () => clearInterval(id);
  }, [isDemo]);

  /* ── Click toggle ── */
  const toggle = useCallback(() => {
    setDemo(false);
    setState((prev) => (prev === "idle" ? "listening" : "idle"));
  }, []);

  return { state, setState, toggle, isDemo, setDemo };
}
