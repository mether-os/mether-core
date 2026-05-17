import { useEffect, useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useMetherStore } from "@/stores/metherStore";
import { Pin, PinOff, X } from "lucide-react";

export function TerminalFeed() {
  const terminalOpen = useMetherStore((s) => s.terminalOpen);
  const setTerminalOpen = useMetherStore((s) => s.setTerminalOpen);
  const terminalLines = useMetherStore((s) => s.terminalLines);
  const terminalCommand = useMetherStore((s) => s.terminalCommand);
  const terminalProcessExit = useMetherStore((s) => s.terminalProcessExit);
  const terminalPinned = useMetherStore((s) => s.terminalPinned);
  const setTerminalPinned = useMetherStore((s) => s.setTerminalPinned);
  
  const [timeLeft, setTimeLeft] = useState<number | null>(null);
  const endOfMessagesRef = useRef<HTMLDivElement>(null);

  // Auto scroll
  useEffect(() => {
    endOfMessagesRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [terminalLines, terminalProcessExit]);

  // Handle auto-close
  useEffect(() => {
    if (terminalProcessExit !== null && !terminalPinned) {
      setTimeLeft(5);
      const interval = setInterval(() => {
        setTimeLeft((prev) => {
          if (prev && prev <= 1) {
            clearInterval(interval);
            setTerminalOpen(false);
            return null;
          }
          return prev ? prev - 1 : null;
        });
      }, 1000);
      return () => clearInterval(interval);
    } else {
      setTimeLeft(null);
    }
  }, [terminalProcessExit, terminalPinned, setTerminalOpen]);

  if (!terminalOpen) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ y: 50, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        exit={{ y: 50, opacity: 0 }}
        transition={{ type: "spring", damping: 25, stiffness: 200 }}
        className="fixed bottom-[100px] left-1/2 -translate-x-1/2 z-40 w-[600px] max-h-[240px] flex flex-col bg-[#050810] border border-primary/30 shadow-[0_0_20px_rgba(6,182,212,0.1)] overflow-hidden"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-3 py-1.5 bg-surface-container border-b border-primary/20 select-none">
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 bg-primary animate-pulse" />
            <span className="text-label-caps text-primary tracking-widest text-[10px]">
              TERMINAL
            </span>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-data-mono text-outline text-[10px] truncate max-w-[200px]">
              {terminalCommand}
            </span>
            <button
              onClick={() => setTerminalPinned(!terminalPinned)}
              className={`hover:text-primary transition-colors ${
                terminalPinned ? "text-primary" : "text-outline"
              }`}
            >
              {terminalPinned ? <PinOff size={12} /> : <Pin size={12} />}
            </button>
            <button
              onClick={() => setTerminalOpen(false)}
              className="text-outline hover:text-error transition-colors"
            >
              <X size={14} />
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-1 font-mono text-[11px] leading-relaxed custom-scrollbar bg-black/40">
          {terminalLines.map((line) => (
            <motion.div
              key={line.id}
              initial={{ x: -10, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              transition={{ duration: 0.1 }}
              className="text-on-surface-variant break-all"
            >
              {line.text}
            </motion.div>
          ))}
          {terminalProcessExit !== null && (
            <motion.div
              initial={{ x: -10, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              className={`mt-2 font-bold ${
                terminalProcessExit === 0 ? "text-success" : "text-error"
              }`}
            >
              [Process exited with code {terminalProcessExit}]
              {timeLeft !== null && !terminalPinned && (
                <span className="text-outline ml-2 font-normal">
                  (closing in {timeLeft}s)
                </span>
              )}
            </motion.div>
          )}
          <div ref={endOfMessagesRef} />
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
