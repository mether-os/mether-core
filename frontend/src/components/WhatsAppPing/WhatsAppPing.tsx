import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useMetherStore } from "@/stores/metherStore";
import type { WAPing } from "@/stores/metherStore";
import { MessageCircle, X, Check } from "lucide-react";

export function WhatsAppPing() {
  const { waActivePings, removePing, socketSend } = useMetherStore();

  // We only show up to 3 pings at a time
  const visiblePings = waActivePings.slice(0, 3);

  const handleRespond = (contact_id: string, contact_name: string, ping_id: string) => {
    if (socketSend) {
      socketSend(JSON.stringify({ type: "handle_start", contact_id, contact_name, ping_id }));
    }
  };

  const handleDismiss = (ping_id: string) => {
    if (socketSend) {
      socketSend(JSON.stringify({ type: "ping_dismissed", ping_id }));
    }
    removePing(ping_id);
  };

  if (visiblePings.length === 0) return null;

  return (
    <div className="fixed top-[48px] right-[260px] z-50 flex flex-col gap-3 pointer-events-none w-[300px]">
      <AnimatePresence>
        {visiblePings.map((ping) => (
          <PingCard
            key={ping.ping_id}
            ping={ping}
            onRespond={() => handleRespond(ping.contact_id, ping.contact_name, ping.ping_id)}
            onDismiss={() => handleDismiss(ping.ping_id)}
          />
        ))}
      </AnimatePresence>
    </div>
  );
}

function PingCard({ ping, onRespond, onDismiss }: { ping: WAPing; onRespond: () => void; onDismiss: () => void }) {
  const [progress, setProgress] = useState(100);

  useEffect(() => {
    const duration = 30000; // 30 seconds
    const interval = 100;
    const step = (interval / duration) * 100;
    
    const timer = setInterval(() => {
      setProgress((prev) => {
        if (prev <= 0) {
          clearInterval(timer);
          onDismiss();
          return 0;
        }
        return prev - step;
      });
    }, interval);
    
    return () => clearInterval(timer);
  }, [onDismiss]);

  return (
    <motion.div
      initial={{ x: 300, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: 300, opacity: 0 }}
      transition={{ type: "spring", stiffness: 300, damping: 30 }}
      className="pointer-events-auto overflow-hidden rounded-lg bg-surface-container border-l-2 border-emerald-500 shadow-xl"
    >
      <div className="p-4 flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-emerald-400">
            <MessageCircle size={16} />
            <span className="font-semibold text-sm truncate max-w-[200px]">{ping.contact_name}</span>
          </div>
          <span className="text-xs text-on-surface-variant">
            {new Date(ping.timestamp * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        </div>
        
        <p className="text-sm text-on-surface line-clamp-2">
          {ping.preview || "Media/Attachment"}
        </p>
        
        <div className="flex gap-2 mt-2">
          <button 
            onClick={onRespond}
            className="flex-1 flex items-center justify-center gap-1 bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-400 text-xs font-medium py-1.5 rounded transition-colors"
          >
            <Check size={14} /> Respond
          </button>
          <button 
            onClick={onDismiss}
            className="flex-1 flex items-center justify-center gap-1 bg-surface-container-high hover:bg-surface-container-highest text-on-surface-variant text-xs font-medium py-1.5 rounded transition-colors"
          >
            <X size={14} /> Dismiss
          </button>
        </div>
      </div>
      
      {/* Progress Bar */}
      <div className="h-1 bg-surface-container-high w-full">
        <div 
          className="h-full bg-emerald-500/50 transition-all duration-100 ease-linear"
          style={{ width: `${progress}%` }}
        />
      </div>
    </motion.div>
  );
}
