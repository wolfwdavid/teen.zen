// src/api/apiBase.ts
const envBase = import.meta.env.VITE_API_BASE_URL?.trim();

function guessBase() {
  // If running inside Capacitor/Android, use emulator host mapping
  const isCapacitor =
    typeof window !== "undefined" &&
    (window as any)?.Capacitor?.isNativePlatform?.();

  if (isCapacitor) return "http://10.0.2.2:8000";

  // Normal web dev in PC browser
  return "http://localhost:8000";
}

export const API_BASE = envBase || guessBase();
