import { useState, useEffect, useRef, useCallback } from "react";
import { useMetherStore } from "@/stores/metherStore";

const WORD_DELAY = 50; // ms between words
const AUTO_CLEAR_MS = 8000;

export default function ResponseDisplay() {
  const activeResponse = useMetherStore((s) => s.activeResponse);
  const setActiveResponse = useMetherStore((s) => s.setActiveResponse);
  const addLog = useMetherStore((s) => s.addLog);
  const setOrbState = useMetherStore((s) => s.setOrbState);

  const [displayText, setDisplayText] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [showCursor, setShowCursor] = useState(true);

  const streamRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const clearTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const streamResponse = useCallback(
    (fullText: string) => {
      // clear any old timers
      if (streamRef.current) clearTimeout(streamRef.current);
      if (clearTimerRef.current) clearTimeout(clearTimerRef.current);

      const words = fullText.split(" ");
      let idx = 0;

      setIsStreaming(true);
      setDisplayText("");
      setOrbState("speaking");

      const tick = () => {
        if (idx < words.length) {
          setDisplayText(words.slice(0, idx + 1).join(" "));
          idx++;
          streamRef.current = setTimeout(tick, WORD_DELAY);
        } else {
          setIsStreaming(false);
          addLog("METHER", fullText);
          setTimeout(() => setOrbState("idle"), 1500);

          // Auto clear after 8 seconds
          clearTimerRef.current = setTimeout(() => {
            setActiveResponse(null);
          }, AUTO_CLEAR_MS);
        }
      };

      tick();
    },
    [addLog, setOrbState, setActiveResponse]
  );

  useEffect(() => {
    if (activeResponse) {
      streamResponse(activeResponse);
    } else {
      setDisplayText("");
      setIsStreaming(false);
    }
  }, [activeResponse, streamResponse]);

  /* Hide cursor when not streaming after a delay */
  useEffect(() => {
    if (!isStreaming && displayText) {
      const id = setTimeout(() => setShowCursor(false), 2000);
      return () => clearTimeout(id);
    }
    setShowCursor(true);
  }, [isStreaming, displayText]);

  if (!displayText) return null;

  return (
    <div
      id="response-display"
      className="fixed left-0 right-0 z-50 flex items-end justify-center px-6 pointer-events-none"
      style={{ bottom: 80 + 8 }}
    >
      <div className="max-w-[800px] w-full flex items-start gap-3 px-5 py-4
                      bg-surface-container-lowest/95 border border-primary/30 backdrop-blur-md shadow-2xl pointer-events-auto max-h-[60vh] overflow-y-auto rounded-sm">
        <span className="text-data-mono text-cyan-400 shrink-0 font-bold tracking-wider pt-0.5" style={{ color: "#00e5ff" }}>
          METHER &gt;
        </span>
        <span className="ai-response-text text-cyan-100 whitespace-pre-wrap leading-relaxed flex-1 text-sm font-mono tracking-wide" style={{ color: "#e0ffff" }}>
          {displayText}
          {showCursor && (
             <span className="inline-block w-2 h-4 bg-cyan-400 ml-1 align-middle" style={{ animation: "flicker 1s steps(2) infinite" }} />
          )}
        </span>
      </div>
    </div>
  );
}
