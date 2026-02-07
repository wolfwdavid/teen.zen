// src/api/apiBase.ts
const envBaseRaw = import.meta.env.VITE_API_BASE_URL?.trim() || "";

function isCapacitorNative() {
  return (
    typeof window !== "undefined" &&
    !!(window as any)?.Capacitor?.isNativePlatform?.()
  );
}

function normalize(base: string) {
  return String(base || "").trim().replace(/\/+$/, "");
}

function pickBase() {
  const native = isCapacitorNative();
  
  // If env is set, use it... except "localhost" on Android must be rewritten.
  if (envBaseRaw) {
    const env = normalize(envBaseRaw);
    if (native && /^http:\/\/localhost(:\d+)?$/i.test(env)) {
      return "http://10.20.50.249:8000";
    }
    return env;
  }
  
  // No env → smart defaults :3
  return native ? "http://10.20.50.249:8000" : "http://localhost:8000";
}

export const API_BASE = pickBase();
export default API_BASE;

