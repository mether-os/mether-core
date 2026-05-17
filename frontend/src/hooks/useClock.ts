import { useState, useEffect } from "react";

/**
 * Live clock hook — returns formatted time string, updated every second.
 * Format: HH:MM:SS (24-hour, zero-padded)
 */
export function useClock(): string {
  const format = (d: Date) =>
    d.toLocaleTimeString("en-GB", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    });

  const [time, setTime] = useState(() => format(new Date()));

  useEffect(() => {
    const id = setInterval(() => setTime(format(new Date())), 1000);
    return () => clearInterval(id);
  }, []);

  return time;
}
