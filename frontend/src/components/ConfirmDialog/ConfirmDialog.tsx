import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useMetherStore } from "@/stores/metherStore";
import { useWebSocket } from "@/hooks/useWebSocket";

export function ConfirmDialog() {
  const pendingConfirmation = useMetherStore((s) => s.pendingConfirmation);
  const setPendingConfirmation = useMetherStore((s) => s.setPendingConfirmation);
  const { send } = useWebSocket();
  const [timeLeft, setTimeLeft] = useState(28);

  const handleExecute = () => {
    if (!pendingConfirmation) return;
    send(
      JSON.stringify({
        type: "confirm_action",
        action_id: pendingConfirmation.action_id,
        approved: true,
      })
    );
    setPendingConfirmation(null);
  };

  const handleCancel = () => {
    if (!pendingConfirmation) return;
    send(
      JSON.stringify({
        type: "confirm_action",
        action_id: pendingConfirmation.action_id,
        approved: false,
      })
    );
    setPendingConfirmation(null);
  };

  useEffect(() => {
    if (!pendingConfirmation) return;

    // eslint-disable-next-line react-hooks/set-state-in-effect
    setTimeLeft(28);
    const interval = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          handleCancel();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pendingConfirmation]);

  if (!pendingConfirmation) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-[100] flex items-center justify-center bg-[#050810]/85">
        <motion.div
          initial={{ opacity: 0, y: 50, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 20, scale: 0.95 }}
          transition={{ type: "spring", damping: 20, stiffness: 300 }}
          className="hud-panel w-[400px] border-l-4 !border-l-amber-500 flex flex-col gap-4 p-5 relative overflow-hidden"
        >
          {/* Scan line effect over the dialog */}
          <div className="absolute inset-0 scan-line-overlay pointer-events-none opacity-50" />

          {/* Header */}
          <div className="flex items-center gap-3">
            <span className="w-2 h-2 bg-amber-500 animate-pulse" />
            <h2 className="hud-label text-amber-500 text-glow-cyan">
              ⚠ CONFIRM ACTION
            </h2>
          </div>

          {/* Body */}
          <div className="flex flex-col gap-2">
            <p className="text-on-surface text-data-mono leading-relaxed">
              {pendingConfirmation.description}
            </p>

            <div className="mt-2 flex items-center gap-2">
              <span className="text-data-mono text-outline text-xs">&gt; TOOL:</span>
              <span className="hud-chip !border-amber-500/50 !text-amber-400 !bg-amber-500/10">
                {pendingConfirmation.tool}
              </span>
            </div>

            {/* Params Viewer (Terminal style) */}
            <div className="mt-3 hud-terminal p-3 bg-surface text-xs text-secondary rounded border border-outline/20">
              {Object.entries(pendingConfirmation.params).map(([key, value]) => (
                <div key={key} className="flex gap-2">
                  <span className="text-outline">{key}:</span>
                  <span className="break-all">{JSON.stringify(value)}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Actions */}
          <div className="mt-4 flex gap-3">
            <button
              onClick={handleExecute}
              className="flex-1 hud-button !border-amber-500 !text-amber-500 hover:!bg-amber-500 hover:!text-[#050810] transition-colors py-2"
            >
              EXECUTE
            </button>
            <button
              onClick={handleCancel}
              className="flex-1 hud-button hover:bg-surface-container transition-colors py-2"
            >
              CANCEL
            </button>
          </div>

          {/* Countdown */}
          <div className="text-center mt-1">
            <span className="text-outline text-xs text-data-mono">
              Auto-cancels in {timeLeft}s
            </span>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
