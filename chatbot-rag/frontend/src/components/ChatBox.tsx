import { useEffect, useMemo, useRef, useState } from "react";
import { askChatbot, healthCheck } from "../api/chat";

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

  // Optional tuning controls
  const [k, setK] = useState(3);
  const [debug, setDebug] = useState(false);

  // Backend badge
  const [backend, setBackend] = useState<BackendState>({ status: "checking" });

  // Abort POST + typing loop
  const abortRef = useRef<AbortController | null>(null);
  const typingTimerRef = useRef<number | null>(null);

  const canAsk = useMemo(() => {
    const hasText = !!question.trim();
    const backendOk = backend.status === "up";
    return hasText && !loading && backendOk;
  }, [question, loading, backend.status]);

  // /health ping on startup (+ interval)
  useEffect(() => {
    const controller = new AbortController();

    async function ping() {
      try {
        setBackend((prev) => ({ ...prev, status: "checking" }));
        const h = await healthCheck({ signal: controller.signal, timeoutMs: 8000 });

        if (h?.ok && h?.initialized && h?.model_loaded) {
          setBackend({
            status: "up",
            detail: "Model ready",
          });
        } else if (h?.ok) {
          setBackend({ 
            status: "down", 
            detail: h?.init_error || "Model not loaded" 
          });
        } else {
          setBackend({ status: "down", detail: "Health check failed" });
        }
      } catch (e: any) {
        setBackend({ status: "down", detail: e?.message ?? "Connection failed" });
      }
    }

    ping();
    const t = window.setInterval(ping, 10000);

    return () => {
      clearInterval(t);
      controller.abort();
    };
  }, []);

  function stop() {
    abortRef.current?.abort();
    abortRef.current = null;

    if (typingTimerRef.current) {
      window.clearTimeout(typingTimerRef.current);
      typingTimerRef.current = null;
    }

    setLoading(false);
  }

  function typewriter(fullText: string, signal: AbortSignal, cps = 80) {
    // cps = chars per second
    const delay = Math.max(5, Math.floor(1000 / cps));
    let i = 0;

    setAnswer("");

    const tick = () => {
      if (signal.aborted) return;

      i = Math.min(fullText.length, i + 1);
      setAnswer(fullText.slice(0, i));

      if (i < fullText.length) {
        typingTimerRef.current = window.setTimeout(tick, delay);
      } else {
        typingTimerRef.current = null;
      }
    };

    tick();
  }

  async function handleAsk() {
    const q = question.trim();
    if (!q) return;

    setLoading(true);
    setAnswer("");
    setSources([]);
    setPerfTime(null);

    stop(); // cancel anything in flight

    const controller = new AbortController();
    abortRef.current = controller;

    const t0 = performance.now();

    try {
      const data: ChatReply = await askChatbot(q, { k, signal: controller.signal, timeoutMs: 120000 });

      const t1 = performance.now();
      setPerfTime(((t1 - t0) / 1000).toFixed(2));

      setSources(Array.isArray(data.sources) ? data.sources : []);

      // ✅ simulate typing
      typewriter(data.answer || "", controller.signal, 90);
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

  const backendBadgeText =
    backend.status === "up"
      ? `✅ Connected — ${backend.detail || "Ready"}`
      : backend.status === "down"
      ? `❌ Offline — ${backend.detail || "Check backend"}`
      : "⏳ Checking backend...";

  const backendBadgeBg =
    backend.status === "up" ? "#dcfce7" : backend.status === "down" ? "#fee2e2" : "#f3f4f6";

  return (
    <div className="chat-box" style={{ maxWidth: 700, margin: "40px auto", padding: 16 }}>
      <div style={{ display: "flex", gap: 12, alignItems: "center", marginBottom: 8, flexWrap: "wrap" }}>
        <div
          style={{
            padding: "4px 10px",
            borderRadius: 999,
            fontSize: 12,
            border: "1px solid #ddd",
            background: backendBadgeBg,
            fontWeight: 500,
          }}
          title={backend.detail || ""}
        >
          {backendBadgeText}
        </div>

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

        <label style={{ display: "flex", gap: 8, alignItems: "center", opacity: 0.7 }}>
          <input type="checkbox" checked={debug} onChange={(e) => setDebug(e.target.checked)} disabled />
          debug
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
        placeholder={backend.status === "down" ? "Backend offline — start server at localhost:8000" : "Ask me anything..."}
        rows={4}
        style={{ width: "100%", padding: 8 }}
        disabled={backend.status !== "up" || loading}
      />

      <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
        <button onClick={handleAsk} disabled={!canAsk}>
          {loading ? "Thinking..." : "Ask"}
        </button>
        <button onClick={stop} disabled={!loading}>
          Stop
        </button>
      </div>

      {perfTime && <div style={{ marginTop: 8, opacity: 0.7, fontSize: 12 }}>Took {perfTime}s</div>}

      <div
        style={{
          marginTop: 16,
          minHeight: 160,
          maxHeight: 380,
          overflowY: "auto",
          background: "#050b1a",
          color: "#dbe8ff",
          padding: 16,
          borderRadius: 10,
          border: "1px solid #1f2a44",
          whiteSpace: "pre-wrap",
          lineHeight: 1.5,
        }}
      >
        {answer || (!loading && <span style={{ opacity: 0.5 }}>No answer yet.</span>)}
      </div>

      {sources.length > 0 && (
        <div style={{ marginTop: 12 }}>
          <div style={{ fontWeight: 600, marginBottom: 6 }}>Sources</div>

          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {sources.map((s, i) => {
              const rank = s.rank ?? i + 1;
              const scoreLabel =
                s.score_type && s.score_type !== "none" ? `${s.score_type}: ${s.score ?? "?"}` : null;

              const label = `[${rank}] ${s.source || "source"}`;

              return (
                <div
                  key={i}
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
            })}
          </div>
        </div>
      )}
    </div>
  );
}