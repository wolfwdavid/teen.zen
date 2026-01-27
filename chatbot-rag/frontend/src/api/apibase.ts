// src/api/apiBase.ts

/**
 * Resolve the backend API base URL safely across:
 * - Web (Vite dev / prod)
 * - Android emulator (10.0.2.2)
 * - Physical devices (LAN IP)
 */

function normalizeBase(url?: string) {
  if (!url) return "";

  let u = url.trim();

  // Guard against missing protocol (common mistake)
  if (u && !/^https?:\/\//i.test(u)) {
    u = `http://${u}`;
  }

  // Remove trailing slashes
  return u.replace(/\/+$/, "");
}

// Priority:
// 1) Vite env var (web / prod builds)
// 2) Android emulator fallback
export const API_BASE = normalizeBase(
  import.meta.env.VITE_API_BASE_URL
) || "http://10.0.2.2:8000";
