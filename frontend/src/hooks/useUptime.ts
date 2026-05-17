import { useState, useEffect, useRef } from "react";

/**
 * Session uptime hook — counts up from 0 on mount.
 * Returns formatted string: HH:MM:SS
 */
export function useUptime(): string {
  const start = useRef(Date.now());
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const id = setInterval(() => {
      setElapsed(Math.floor((Date.now() - start.current) / 1000));
    }, 1000);
    return () => clearInterval(id);
  }, []);

  const h = String(Math.floor(elapsed / 3600)).padStart(2, "0");
  const m = String(Math.floor((elapsed % 3600) / 60)).padStart(2, "0");
  const s = String(elapsed % 60).padStart(2, "0");

  return `${h}:${m}:${s}`;
}
