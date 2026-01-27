// src/components/ChatBoxStream.jsx
import { useEffect, useRef, useState } from "react";
import { API_BASE } from "../api/apiBase"; // ✅ use your real base URL

function joinUrl(base, path) {
  const b = String(base || "").trim().replace(/\/+$/, "");
  const p = String(path || "").replace(/^\/+/, "");
  return `${b}/${p}`;
}

export default function ChatBoxStream() {
  const [q, setQ] = useState("");
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState([]);
  const [streaming, setStreaming] = useState(false);
  const [err, setErr] = useState("");
  const esRef = useRef(null);
  const outRef = useRef(null);

  useEffect(() => {
    if (outRef.current) outRef.current.scrollTop = outRef.current.scrollHeight;
  }, [answer]);

  const stop = () => {
    setStreaming(false);
    if (esRef.current) {
      try {
        esRef.current.close();
      } catch {}
      esRef.current = null;
    }
  };

  const start = () => {
    if (!q.trim() || streaming) return;

    setAnswer("");
    setSources([]);
    setErr("");
    setStreaming(true);

    // ✅ ABSOLUTE URL (required for Android/Capacitor)
    const url = joinUrl(API_BASE, "/chat/stream") + `?q=${encodeURIComponent(q.trim())}&k=3&heartbeat=2`;

    let es;
    try {
      es = new EventSource(url);
    } catch (e) {
      setErr(`Failed to create EventSource. API_BASE=${API_BASE}`);
      setStreaming(false);
      return;
    }

    esRef.current = es;

    es.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data);

        if (msg.type === "sources") {
          setSources(Array.isArray(msg.items) ? msg.items : []);
          return;
        }

        if (msg.type === "token") {
          setAnswer((prev) => prev + (msg.text || ""));
          return;
        }

        if (msg.type === "error") {
          setErr(msg.error || msg.message || "Streaming error");
          stop();
          return;
        }

        if (msg.type === "done") {
          stop();
          return;
        }
      } catch {
        // ignore non-JSON lines
      }
    };

    es.onerror = () => {
      setErr(
        `Connection lost (SSE). Check emulator reachability:\n` +
          `1) Open ${joinUrl(API_BASE, "/health")} in emulator Chrome\n` +
          `2) Ensure backend runs with --host 0.0.0.0\n` +
          `API_BASE=${API_BASE}`
      );
      stop();
    };
  };

  return (
    <div style={{ maxWidth: 900, margin: "24px auto", padding: 16 }}>
      <h1 style={{ color: "#fff", margin: "0 0 12px" }}>RAG Chat (Streaming)</h1>

      <div style={{ color: "#cbd5e1", fontSize: 12, marginBottom: 8 }}>
        API: <span style={{ color: "#93c5fd" }}>{API_BASE}</span>
      </div>

      <textarea
        value={q}
        onChange={(e) => setQ(e.target.value)}
        rows={3}
        placeholder="Ask something…"
        style={{
          width: "100%",
          padding: 12,
          borderRadius: 8,
          border: "1px solid #3a3f4b",
          background: "#2c2f36",
          color: "#e8ecf5",
        }}
      />

      <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
        <button
          onClick={start}
          disabled={streaming || !q.trim()}
          style={{
            padding: "8px 12px",
            borderRadius: 8,
            border: "1px solid #3a3f4b",
            background: streaming ? "#333b" : "#1e293b",
            color: "#e8ecf5",
            cursor: streaming ? "not-allowed" : "pointer",
          }}
        >
          {streaming ? "Streaming…" : "Ask (Streaming)"}
        </button>

        <button
          onClick={stop}
          disabled={!streaming}
          style={{
            padding: "8px 12px",
            borderRadius: 8,
            border: "1px solid #3a3f4b",
            background: "#374151",
            color: "#e8ecf5",
          }}
        >
          Stop
        </button>
      </div>

      <div
        ref={outRef}
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
        {answer || (!streaming && <span style={{ opacity: 0.5 }}>No answer yet.</span>)}
      </div>

      {sources.length > 0 && (
        <div style={{ marginTop: 10, display: "flex", gap: 8, flexWrap: "wrap" }}>
          {sources.map((s, i) => (
            <span
              key={i}
              title={s.preview || ""}
              style={{
                padding: "6px 10px",
                borderRadius: 8,
                background: "#0b1b3a",
                border: "1px solid #1f3b7a",
                color: "#a3c4ff",
              }}
            >
              [{s.rank ?? i + 1}] {s.source || "source"}
            </span>
          ))}
        </div>
      )}

      {err && (
        <div style={{ marginTop: 10, color: "#ff7b7b", whiteSpace: "pre-wrap" }}>
          <strong>Error:</strong> {err}
        </div>
      )}
    </div>
  );
}
