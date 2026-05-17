import { useState, useEffect, useRef, useCallback } from "react";
import { useMetherStore } from "@/stores/metherStore";

/* ═══════════════════════════════════════════════════════════════
   METHER OS — AI Response Streamer

   Demo mode: simulates AI responses with word-by-word typewriter.
   Picks a random response every 5 seconds, streams it into
   both a visible display area AND the agent log store.
   ═══════════════════════════════════════════════════════════════ */

const AI_RESPONSES = [
  "Analyzing your calendar for tomorrow. Found 2 conflicts.",
  "Gmail scan complete. 3 emails flagged for reply.",
  "Memory context loaded. 847 vectors indexed.",
  "WhatsApp bridge nominal. 12 unread messages detected.",
  "Running system diagnostics... All systems nominal.",
  "Voice pipeline ready. Whisper model loaded.",
  "ChromaDB sync complete. 1,204 embeddings refreshed.",
  "Task queue processed. 0 pending, 3 completed.",
  "Security scan: no anomalies. Firewall rules active.",
  "Model inference latency: 42ms. Performance optimal.",
];

const WORD_DELAY = 80; // ms between words
const RESPONSE_INTERVAL = 5000; // ms between new responses

export default function AIResponseStreamer() {
  const [displayText, setDisplayText] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [showCursor, setShowCursor] = useState(true);
  const isDemo = useMetherStore((s) => s.isDemo);
  const addLog = useMetherStore((s) => s.addLog);
  const setOrbState = useMetherStore((s) => s.setOrbState);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const streamRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  /* ── Stream a single response word by word ── */
  const streamResponse = useCallback(
    (fullText: string) => {
      const words = fullText.split(" ");
      let idx = 0;

      setIsStreaming(true);
      setDisplayText("");
      setOrbState("speaking");

      const tick = () => {
        if (idx < words.length) {
          setDisplayText((prev) => (prev ? prev + " " + words[idx] : words[idx]));
          idx++;
          streamRef.current = setTimeout(tick, WORD_DELAY);
        } else {
          // Done streaming
          setIsStreaming(false);
          addLog("METHER", fullText);
          setTimeout(() => setOrbState("idle"), 1500);
        }
      };

      tick();
    },
    [addLog, setOrbState]
  );

  /* ── Pick and stream random responses on interval ── */
  useEffect(() => {
    if (!isDemo) return;

    // Initial delay before first response
    const initialDelay = setTimeout(() => {
      const pick = () => {
        const text = AI_RESPONSES[Math.floor(Math.random() * AI_RESPONSES.length)];
        streamResponse(text);
      };

      pick();
      timerRef.current = setInterval(pick, RESPONSE_INTERVAL) as unknown as ReturnType<typeof setTimeout>;
    }, 2000);

    return () => {
      clearTimeout(initialDelay);
      if (timerRef.current) clearInterval(timerRef.current as unknown as number);
      if (streamRef.current) clearTimeout(streamRef.current);
    };
  }, [isDemo, streamResponse]);

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
      id="ai-response-display"
      className="fixed left-0 right-0 z-50 flex items-center justify-center px-6"
      style={{ bottom: 80 + 8, height: 36 }}
    >
      <div className="max-w-[600px] w-full flex items-center gap-2 px-4 py-1.5
                      bg-surface-container-lowest/80 border border-primary/15 backdrop-blur-sm">
        <span className="text-data-mono text-primary shrink-0 font-bold tracking-wider">
          METHER &gt;
        </span>
        <span className="ai-response-text truncate">
          {displayText}
          {showCursor && <span className="ai-response-cursor" />}
        </span>
      </div>
    </div>
  );
}
