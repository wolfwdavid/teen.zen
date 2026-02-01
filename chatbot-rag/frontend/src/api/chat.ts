import { API_BASE } from "./apiBase";

// ✅ Updated types to support retrieval scoring visibility
export type SourceItem = {
  id: number;
  rank?: number; // 1 = best result
  source: string;
  href?: string;
  preview?: string;

  // Retrieval diagnostics (optional for backward compatibility)
  score_type?: "relevance" | "distance" | "none";
  score?: number | null;
};

export type ChatReply = {
  answer: string;
  sources: SourceItem[];
};

// --- URL helpers ---
function normalizeBase(base: string) {
  // Defend against trailing spaces
  const b = (base || "").trim().replace(/\/+$/, "");

  // ✅ URL() requires an absolute URL
  if (!/^https?:\/\//i.test(b)) {
    throw new Error(
      `API_BASE must be an absolute URL starting with http:// or https:// (got: "${base}")`
    );
  }

  return b;
}

function joinUrl(base: string, path: string) {
  const b = normalizeBase(base);
  const p = (path || "").replace(/^\/+/, "");
  return `${b}/${p}`;
}

function buildUrl(
  base: string,
  path: string,
  query?: Record<string, string | number | boolean | undefined>
) {
  const url = new URL(joinUrl(base, path));
  if (query) {
    for (const [k, v] of Object.entries(query)) {
      if (v === undefined) continue;
      url.searchParams.set(k, String(v));
    }
  }
  return url.toString();
}

// --- Small fetch utilities ---
async function safeText(res: Response) {
  try {
    return await res.text();
  } catch {
    return "";
  }
}

function withTimeout(signal?: AbortSignal, ms = 30000) {
  const controller = new AbortController();

  const onAbort = () => controller.abort();
  if (signal) {
    if (signal.aborted) controller.abort();
    else signal.addEventListener("abort", onAbort, { once: true });
  }

  const timer = setTimeout(() => controller.abort(), ms);

  const cleanup = () => {
    clearTimeout(timer);
    if (signal) signal.removeEventListener("abort", onAbort);
  };

  return { signal: controller.signal, cleanup };
}

// --- API calls ---
export async function askChatbot(
  question: string,
  opts?: { k?: number; signal?: AbortSignal; timeoutMs?: number }
): Promise<ChatReply> {
  const url = buildUrl(API_BASE, "/chat");
  const { signal, cleanup } = withTimeout(opts?.signal, opts?.timeoutMs ?? 30000);

  try {
    const body: Record<string, unknown> = { question };
    if (opts?.k !== undefined) body.k = opts.k;

    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal,
    });

    if (!res.ok) {
      const text = await safeText(res);
      throw new Error(
        `HTTP ${res.status} ${res.statusText}${text ? ` — ${text}` : ""}`
      );
    }

    return (await res.json()) as ChatReply;
  } finally {
    cleanup();
  }
}

/**
 * Streaming endpoint URL builder (used by ChatBox).
 * Adds optional k/debug/heartbeat query params.
 */
export function chatStreamUrl(
  question: string,
  opts?: { k?: number; debug?: 0 | 1; heartbeat?: number }
) {
  return buildUrl(API_BASE, "/api/chat/stream", {
    q: question,
    k: opts?.k ?? 3,
    debug: opts?.debug ?? 0,
    heartbeat: opts?.heartbeat ?? 0, // 0 disables heartbeat
  });
}

/**
 * Handy health URL (useful to test from device WebView / browser)
 */
export function healthUrl() {
  return buildUrl(API_BASE, "/health");
}

// --- Health check ---
export type HealthReply = {
  ok: boolean;
  initialized?: boolean;
  model_loaded?: boolean;
  init_error?: string | null;
};

export async function healthCheck(opts?: {
  signal?: AbortSignal;
  timeoutMs?: number;
}): Promise<HealthReply> {
  const url = buildUrl(API_BASE, "/health");
  const { signal, cleanup } = withTimeout(opts?.signal, opts?.timeoutMs ?? 8000);

  try {
    const res = await fetch(url, {
      method: "GET",
      headers: { Accept: "application/json" },
      signal,
    });

    if (!res.ok) {
      const text = await safeText(res);
      throw new Error(
        `HTTP ${res.status} ${res.statusText}${text ? ` — ${text}` : ""}`
      );
    }

    return (await res.json()) as HealthReply;
  } finally {
    cleanup();
  }
}
