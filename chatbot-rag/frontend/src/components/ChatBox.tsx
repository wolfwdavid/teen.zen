import { useEffect, useMemo, useRef, useState } from "react";
import { askChatbot, chatStreamUrl, healthCheck } from "../api/chat"; // ✅ use helpers from chat.ts

type SourceItem = {
  id: number;
  rank?: number;
  source: string;
  href?: string;
  preview?: string;
  score_type?: "relevance" | "distance" | "none";
  score?: number | null;
};

type ChatReply = {
  answer: string;
  sources: SourceItem[];
};

type StreamEvent =
  | { type: "sources"; items: SourceItem[] }
  | { type: "token"; text: string }
  | { type: "perf_time"; data: string }
  | { type: "done" }
  | { type: "error"; error: string };

type BackendState = {
  status: "checking" | "up" | "down";
  detail?: string;
};

export default function ChatBox() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState<SourceItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [perfTime, setPerfTime] = useState<string | null>(null);
  const [useStreaming, setUseStreaming] = useState(true);

  // Optional tuning controls (easy to remove)
  const [k, setK] = useState(3);
  const [debug, setDebug] = useState(false);

  // ✅ Backend health badge
  const [backend, setBackend] = useState<BackendState>({ status: "checking" });

  const abortRef = useRef<AbortController | null>(null);

  const canAsk = useMemo(() => {
    const hasText = !!question.trim();
    const backendOk = backend.status === "up";
    return hasText && !loading && backendOk;
  }, [question, loading, backend.status]);

  // ✅ /health ping on startup (+ interval refresh)
  useEffect(() => {
    const controller = new AbortController();

    async function ping() {
      try {
        setBackend((prev) => ({ ...prev, status: "checking" }));
        const h = await healthCheck({ signal: controller.signal, timeoutMs: 8000 });

        if (h?.ok) {
          const ready = !!h.initialized && !!h.model_loaded;
          setBackend({
            status: "up",
            detail: ready ? "Model ready" : "Backend up (warming)",
          });
        } else {
          setBackend({ status: "down", detail: "Health returned ok=false" });
        }
      } catch (e: any) {
        setBackend({ status: "down", detail: e?.message ?? String(e) });
      }
    }

    ping();
    const t = setInterval(ping, 10000);

    return () => {
      clearInterval(t);
      controller.abort();
    };
  }, []);

  function stop() {
    abortRef.current?.abort();
    abortRef.current = null;
    setLoading(false);
  }

  async function handleAsk() {
    const q = question.trim();
    if (!q) return;

    setLoading(true);
    setAnswer("");
    setSources([]);
    setPerfTime(null);

    // Cancel any previous request
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    try {
      // 1) Try SSE first (if enabled)
      if (useStreaming) {
        const ok = await tryStream(q, controller.signal);
        if (ok) return;
        // if SSE hard-failed before starting, we fall through to POST
      }

      // 2) Fallback to normal POST
      const data: ChatReply = await askChatbot(q, { k, signal: controller.signal, timeoutMs: 60000 });
      setAnswer(data.answer || "");
      setSources(Array.isArray(data.sources) ? data.sources : []);
    } catch (err: any) {
      if (err?.name === "AbortError") {
        setAnswer("(stopped)");
      } else {
        setAnswer("Error: " + (err?.message ?? String(err)));
      }
    } finally {
      setLoading(false);
      abortRef.current = null;
    }
  }

  async function tryStream(q: string, signal: AbortSignal): Promise<boolean> {
    // ✅ Use your helper, with heartbeat to keep Android/proxies alive
    const url = chatStreamUrl(q, { k, debug: debug ? 1 : 0, heartbeat: 2 });

    let res: Response;
    try {
      res = await fetch(url, {
        method: "GET",
        headers: {
          Accept: "text/event-stream",
          "Cache-Control": "no-cache",
        },
        signal,
      });
    } catch {
      // Network-level failure: let caller fall back to POST
      return false;
    }

    // If server isn't reachable, fall back to POST
    if (!res.ok || !res.body) return false;

    const reader = res.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    // IMPORTANT: local flag (don’t rely on React state inside long loops)
    let gotAnyToken = false;

    const handleEvent = (evt: StreamEvent) => {
      if (evt.type === "sources") {
        setSources(Array.isArray(evt.items) ? evt.items : []);
      } else if (evt.type === "token") {
        gotAnyToken = true;
        setAnswer((prev) => prev + (evt.text ?? ""));
      } else if (evt.type === "perf_time") {
        setPerfTime(evt.data ?? null);
      } else if (evt.type === "error") {
        setAnswer("Error: " + (evt.error ?? "unknown error"));
      }
    };

    try {
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // SSE frames separated by blank line
        const frames = buffer.split("\n\n");
        buffer = frames.pop() ?? "";

        for (const frame of frames) {
          // Ignore heartbeats/comments like ":" frames
          if (frame.startsWith(":")) continue;

          // SSE can contain multiple data: lines; join them.
          const dataLines = frame
            .split("\n")
            .filter((l) => l.startsWith("data:"))
            .map((l) => l.replace(/^data:\s*/, ""));

          if (!dataLines.length) continue;

          const payload = dataLines.join("\n").trim();
          if (!payload) continue;

          let evt: StreamEvent | null = null;
          try {
            evt = JSON.parse(payload);
          } catch {
            continue;
          }
          if (!evt) continue;

          if (evt.type === "done") {
            return true;
          }

          handleEvent(evt);
        }
      }

      // Stream ended without done:
      // - If we got tokens, treat as success.
      // - If we got nothing, return false so caller falls back to POST.
      return gotAnyToken;
    } catch (err: any) {
      if (err?.name === "AbortError") return true; // user hit Stop

      // If it drops mid-stream on Android:
      // - If we already have tokens, keep what we have (success-ish).
      // - If not, fall back to POST.
      if (gotAnyToken) {
        setAnswer((prev) => prev + "\n\n(⚠️ stream interrupted)");
        return true;
      }
      return false;
    } finally {
      try {
        await reader.cancel();
      } catch {}
    }
  }

  const backendBadgeText =
    backend.status === "up"
      ? `Backend connected ✅${backend.detail ? ` — ${backend.detail}` : ""}`
      : backend.status === "down"
      ? `Backend offline ❌${backend.detail ? ` — ${backend.detail}` : ""}`
      : "Checking backend…";

  const backendBadgeBg =
    backend.status === "up" ? "#dcfce7" : backend.status === "down" ? "#fee2e2" : "#f3f4f6";

  return (
    <div className="chat-box" style={{ maxWidth: 700, margin: "40px auto", padding: 16 }}>
      <div style={{ display: "flex", gap: 12, alignItems: "center", marginBottom: 8, flexWrap: "wrap" }}>
        {/* ✅ Backend badge */}
        <div
          style={{
            padding: "4px 10px",
            borderRadius: 999,
            fontSize: 12,
            border: "1px solid #ddd",
            background: backendBadgeBg,
          }}
          title={backend.detail || ""}
        >
          {backendBadgeText}
        </div>

        <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <input
            type="checkbox"
            checked={useStreaming}
            onChange={(e) => setUseStreaming(e.target.checked)}
            disabled={loading}
          />
          Streaming
        </label>

        <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
          k:
          <input
            type="number"
            min={1}
            max={20}
            value={k}
            disabled={loading}
            onChange={(e) => setK(Math.max(1, Math.min(20, Number(e.target.value) || 3)))}
            style={{ width: 64 }}
          />
        </label>

        <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <input type="checkbox" checked={debug} onChange={(e) => setDebug(e.target.checked)} disabled={loading} />
          Debug
        </label>

        {loading ? (
          <button onClick={stop} style={{ marginLeft: "auto" }}>
            Stop
          </button>
        ) : null}
      </div>

      <textarea
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleAsk();
          }
        }}
        placeholder={backend.status === "down" ? "Backend is offline — start the server first" : "Ask me anything..."}
        rows={4}
        style={{ width: "100%", padding: 8 }}
        disabled={backend.status !== "up" || loading}
      />

      <button onClick={handleAsk} disabled={!canAsk} style={{ marginTop: 8 }}>
        {loading ? "Thinking..." : useStreaming ? "Ask (SSE Typing)" : "Ask"}
      </button>

      {perfTime && <div style={{ marginTop: 8, opacity: 0.7, fontSize: 12 }}>Took {perfTime}s</div>}

      {answer && (
        <div style={{ marginTop: 12, whiteSpace: "pre-wrap", lineHeight: 1.5 }}>
          <strong>Answer:</strong> {answer}
        </div>
      )}

      {sources.length > 0 && (
        <div style={{ marginTop: 12 }}>
          <div style={{ fontWeight: 600, marginBottom: 6 }}>Sources</div>

          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {sources.map((s, i) => {
              const rank = s.rank ?? i + 1;
              const scoreLabel =
                s.score_type && s.score_type !== "none" ? `${s.score_type}: ${s.score ?? "?"}` : null;

              const label = `[${rank}] ${s.source || "source"}`;

              const chip = (
                <div
                  title={s.preview || ""}
                  style={{
                    padding: "6px 10px",
                    borderRadius: 10,
                    background: "#eef2ff",
                    border: "1px solid #c7d2fe",
                    display: "flex",
                    gap: 8,
                    alignItems: "center",
                  }}
                >
                  <span style={{ color: "#1d4ed8" }}>{label}</span>
                  {scoreLabel ? (
                    <span
                      style={{
                        fontSize: 12,
                        padding: "2px 6px",
                        borderRadius: 999,
                        background: "#e0e7ff",
                        border: "1px solid #c7d2fe",
                        opacity: 0.9,
                      }}
                    >
                      {scoreLabel}
                    </span>
                  ) : null}
                </div>
              );

              return s.href ? (
                <a key={i} href={s.href} target="_blank" rel="noreferrer" style={{ textDecoration: "none" }}>
                  {chip}
                </a>
              ) : (
                <div key={i}>{chip}</div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
