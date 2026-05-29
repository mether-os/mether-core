import { motion, AnimatePresence } from "framer-motion";
import { useMetherStore } from "@/stores/metherStore";

export function WhatsAppQRModal() {
  const whatsappQR = useMetherStore((s) => s.whatsappQR);
  const whatsappStatus = useMetherStore((s) => s.whatsappStatus);
  const isDemo = useMetherStore((s) => s.isDemo);

  // Only show the modal when NOT in demo mode, whatsappStatus is disconnected, and a QR code is available.
  const showModal = !isDemo && whatsappStatus === "disconnected" && !!whatsappQR;

  if (!showModal) return null;

  const qrImageUrl = `https://api.qrserver.com/v1/create-qr-code/?size=250x250&data=${encodeURIComponent(whatsappQR)}`;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-[100] flex items-center justify-center bg-[#050810]/85">
        <motion.div
          initial={{ opacity: 0, y: 50, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 20, scale: 0.95 }}
          transition={{ type: "spring", damping: 20, stiffness: 300 }}
          className="hud-panel w-[350px] flex flex-col items-center gap-4 p-6 relative overflow-hidden"
          style={{
            border: "1px solid rgba(76, 215, 246, 0.3)",
            boxShadow: "0 0 25px rgba(76, 215, 246, 0.15)",
          }}
        >
          {/* Scan line effect */}
          <div className="absolute inset-0 scan-line-overlay pointer-events-none opacity-40" />

          {/* Header */}
          <div className="flex items-center gap-2 self-start w-full">
            <span className="w-2 h-2 rounded-full bg-success animate-ping" />
            <h2 className="hud-label text-primary text-glow-cyan">
              LINK WHATSAPP
            </h2>
          </div>

          <div className="text-[10px] text-outline text-data-mono self-start mb-1">
            Scan the QR code below to connect METHER OS to your WhatsApp account.
          </div>

          {/* QR Code Container */}
          <div 
            className="p-3 bg-white rounded-lg flex items-center justify-center relative shadow-inner"
            style={{
              border: "2px solid rgba(76, 215, 246, 0.4)",
              boxShadow: "0 0 15px rgba(76, 215, 246, 0.2)",
            }}
          >
            <img 
              src={qrImageUrl} 
              alt="WhatsApp QR Code" 
              className="w-[200px] h-[200px] block" 
            />
          </div>

          {/* Status info */}
          <div className="text-center mt-2 flex flex-col gap-1 w-full">
            <div className="text-data-mono text-[9px] text-outline uppercase tracking-widest">
              Status: <span className="text-warning font-bold">Awaiting Scan...</span>
            </div>
            <div className="text-[8px] text-outline-variant font-mono">
              The QR code updates periodically.
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
