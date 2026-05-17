import { useState, useRef, useCallback, useEffect, type KeyboardEvent } from "react";
import { Send, Mic } from "lucide-react";

/* ═══════════════════════════════════════════════════════════════
   METHER OS — Command Input Bar

   Full-width command bar positioned just above the bottom status bar.
   • Enter / SEND → submit command
   • Escape → clear input
   • Up arrow → cycle command history
   • Blinking block cursor on focus
   • Flash animation on submit
   ═══════════════════════════════════════════════════════════════ */

interface CommandInputProps {
  onSubmit: (command: string) => void;
  commandHistory: string[];
  isConnected: boolean;
}

import { useMetherStore } from "@/stores/metherStore";

export default function CommandInput({
  onSubmit,
  commandHistory,
  isConnected,
}: CommandInputProps) {
  const [value, setValue] = useState("");
  const [historyIdx, setHistoryIdx] = useState(-1);
  const [isFocused, setIsFocused] = useState(false);
  const [flashKey, setFlashKey] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  
  const setActiveResponse = useMetherStore((s) => s.setActiveResponse);

  /* ── Submit ── */
  const handleSubmit = useCallback(() => {
    const trimmed = value.trim();
    if (!trimmed) return;

    if (!isConnected) {
      setActiveResponse("[OFFLINE] Cannot process command");
    }

    onSubmit(trimmed);
    setValue("");
    setHistoryIdx(-1);
    setFlashKey((k) => k + 1); // trigger flash animation
  }, [value, onSubmit, isConnected, setActiveResponse]);

  /* ── Keyboard ── */
  const handleKey = useCallback(
    (e: KeyboardEvent<HTMLInputElement>) => {
      switch (e.key) {
        case "Enter":
          e.preventDefault();
          handleSubmit();
          break;

        case "Escape":
          e.preventDefault();
          setValue("");
          setHistoryIdx(-1);
          break;

        case "ArrowUp": {
          e.preventDefault();
          if (commandHistory.length === 0) return;
          const nextIdx = historyIdx + 1;
          if (nextIdx < commandHistory.length) {
            setHistoryIdx(nextIdx);
            setValue(commandHistory[commandHistory.length - 1 - nextIdx]);
          }
          break;
        }

        case "ArrowDown": {
          e.preventDefault();
          if (historyIdx <= 0) {
            setHistoryIdx(-1);
            setValue("");
          } else {
            const nextIdx = historyIdx - 1;
            setHistoryIdx(nextIdx);
            setValue(commandHistory[commandHistory.length - 1 - nextIdx]);
          }
          break;
        }
      }
    },
    [handleSubmit, commandHistory, historyIdx]
  );

  /* ── Global Keyboard Shortcuts ── */
  useEffect(() => {
    const handleGlobalKey = (e: globalThis.KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };
    window.addEventListener("keydown", handleGlobalKey);
    return () => window.removeEventListener("keydown", handleGlobalKey);
  }, []);

  return (
    <div
      key={flashKey}
      id="hud-command-bar"
      className={`fixed left-0 right-0 z-50 flex items-center gap-3 px-4
                 bg-surface-container-low border-t border-primary/15 select-none
                 ${flashKey > 0 ? "cmd-flash" : ""}`}
      style={{ bottom: 32, height: 48 }}
    >
      {/* ── Prompt prefix ── */}
      <span className="text-label-caps text-primary text-glow-cyan tracking-[0.12em] shrink-0 text-[11px]">
        &gt; METHER://
      </span>

      {/* ── Connection indicator dot ── */}
      <span
        className={`w-[5px] h-[5px] rounded-full shrink-0 ${
          isConnected ? "bg-success" : "bg-error"
        }`}
        style={{ animation: "breathe 2s ease-in-out infinite" }}
      />

      {/* ── Input ── */}
      <div className="flex-1 relative">
        <input
          ref={inputRef}
          type="text"
          value={value}
          onChange={(e) => {
            setValue(e.target.value);
            setHistoryIdx(-1);
          }}
          onKeyDown={handleKey}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          placeholder="ENTER DIRECTIVE..."
          spellCheck={false}
          autoComplete="off"
          className={`w-full bg-transparent font-mono text-sm text-primary
                     placeholder:text-outline-variant/50 placeholder:tracking-[0.15em]
                     border-none outline-none tracking-wider
                     border-b border-b-primary/20 pb-0.5
                     caret-transparent transition-all duration-200
                     ${isFocused ? "shadow-[0_4px_12px_rgba(76,215,246,0.1)]" : ""}`}
          style={{
            borderBottom: `1px solid rgba(76, 215, 246, ${isFocused ? 0.6 : 0.2})`,
          }}
        />

        {/* Blinking block cursor */}
        {isFocused && (
          <span
            className="absolute top-1/2 -translate-y-1/2 w-[8px] h-[14px] bg-primary/80 pointer-events-none"
            style={{
              left: `${value.length * 8.4 + 1}px`,
              animation: "flicker 1s steps(2) infinite",
            }}
          />
        )}
      </div>

      {/* ── Hint ── */}
      <span className="hidden md:inline text-[9px] font-mono text-outline-variant/40 shrink-0 pointer-events-none pr-1">
        CTRL+K
      </span>

      {/* ── Mic button ── */}
      <button
        type="button"
        className="hud-button !p-2 !border-primary/30"
        title="Voice input"
      >
        <Mic size={14} />
      </button>

      {/* ── Send button ── */}
      <button
        type="button"
        onClick={handleSubmit}
        disabled={!value.trim()}
        className="hud-button !py-1.5 !px-3 !text-[9px]"
      >
        <span className="hidden md:inline">EXECUTE</span>
        <Send size={12} className="md:ml-1" />
      </button>
    </div>
  );
}
