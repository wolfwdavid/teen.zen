// src/components/ChatBoxStream.jsx
import { useEffect, useRef, useState } from "react";

export default function ChatBoxStream() {
  const [q, setQ] = useState("");
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState([]);
  const [streaming, setStreaming] = useState(false);
  const [err, setErr] = useState("");
  const esRef = useRef(null);
  const outRef = useRef(null);

  // autoscroll as text grows
  useEffect(() => {
    if (outRef.current) outRef.current.scrollTop = outRef.current.scrollHeight;
  }, [answer]);

  const start = () => {
    if (!q.trim() || streaming) return;

    // reset UI
    setAnswer("");
    setSources([]);
    setErr("");
    setStreaming(true);

    // open SSE
    const url = `/chat/stream?q=${encodeURIComponent(q.trim())}`;
    const es = new EventSource(url, { withCredentials: false });
    esRef.current = es;

    es.onmessage = (evt) => {
      // evt.data is a JSON string from the backend
      try {
        const msg = JSON.parse(evt.data);

        if (msg.type === "status") return;

        if (msg.type === "sources") {
          setSources(Array.isArray(msg.items) ? msg.items : []);
          return;
        }

        if (msg.type === "token") {
          // append the token
          setAnswer((prev) => prev + msg.text);
          return;
        }

        if (msg.type === "error") {
          setErr(msg.message || "Streaming error");
          stop();
          return;
        }

        if (msg.type === "done") {
          stop();
          return;
        }
      } catch (e) {
        // non-JSON lines are ignored
      }
    };

    es.onerror = () => {
      setErr("Connection lost (SSE onerror).");
      stop();
    };
  };

  const stop = () => {
    setStreaming(false);
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }
  };

  return (
    <div style={{ maxWidth: 900, margin: "24px auto", padding: 16 }}>
      <h1 style={{ color: "#fff", margin: "0 0 12px" }}>
        RAG Chat (Streaming + Typing)
      </h1>

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
          {streaming ? "Streaming…" : "Ask (SSE Typing)"}
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

      {/* OUTPUT */}
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

      {/* SOURCES */}
      {sources.length > 0 && (
        <div style={{ marginTop: 10, display: "flex", gap: 8, flexWrap: "wrap" }}>
          {sources.map((s, i) => {
            const label = `[${i + 1}] ${s.source || "source"}`;
            const title = s.preview || s.metadata?.source || "";
            const href =
              s.href ||
              (s.source && s.source.startsWith("docs/") ? `/${s.source.replace(/^\//, "")}` : null);
            return href ? (
              <a
                key={i}
                href={href}
                target="_blank"
                rel="noreferrer"
                title={title}
                style={{
                  padding: "6px 10px",
                  borderRadius: 8,
                  background: "#0b1b3a",
                  border: "1px solid #1f3b7a",
                  color: "#a3c4ff",
                  textDecoration: "none",
                }}
              >
                {label}
              </a>
            ) : (
              <span
                key={i}
                title={title}
                style={{
                  padding: "6px 10px",
                  borderRadius: 8,
                  background: "#0b1b3a",
                  border: "1px solid #1f3b7a",
                  color: "#a3c4ff",
                }}
              >
                {label}
              </span>
            );
          })}
        </div>
      )}

      {err && (
        <div style={{ marginTop: 10, color: "#ff7b7b" }}>
          <strong>Error:</strong> {err}
        </div>
      )}
    </div>
  );
}
