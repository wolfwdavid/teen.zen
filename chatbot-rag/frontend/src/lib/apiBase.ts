// apiBase.ts

/**
 * Priority order:
 * 1. VITE_API_BASE_URL (explicit env override)
 * 2. Capacitor injected server URL (mobile)
 * 3. Local dev fallback
 */

export const API_BASE =
  import.meta.env.VITE_API_BASE_URL ??
  (window as any)?.Capacitor?.getPlatform?.()
    ? "http://10.0.2.2:8000" // Android emulator → localhost
    : "http://127.0.0.1:8000";
