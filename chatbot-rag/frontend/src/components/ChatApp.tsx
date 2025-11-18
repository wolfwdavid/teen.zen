import { useEffect, useMemo, useRef, useState } from "react";
import { useDarkMode } from "../hooks/useDarkMode/useDarkMode";

type Role = "user" | "assistant";
type Source = { id: number; source: string; href?: string; preview?: string };
type Message = { id: string; role: Role; text: string; sources?: Source[] };

function newId() {
  return Math.random().toString(36).slice(2);
}

export default function ChatApp() {
  const [theme, toggleTheme] = useDarkMode(); // ⬅️ add
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);

  // Auto scroll
  const endRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  const streamUrl = useMemo(() => (q: string) => `/chat/stream?q=${encodeURIComponent(q)}`, []);

  const ask = async () => {
    const question = input.trim();
    if (!question || busy) return;

    setBusy(true);
    setInput("");

    const userMsg: Message = { id: newId(), role: "user", text: question };
    setMessages((prev) => [...prev, userMsg]);

    const asstId = newId();
    setMessages((prev) => [...prev, { id: asstId, role: "assistant", text: "" }]);

    const es = new EventSource(streamUrl(question));
    es.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data);
        if (msg.type === "sources") {
          setMessages((prev) => prev.map((m) => (m.id === asstId ? { ...m, sources: msg.items ?? [] } : m)));
          return;
        }
        if (msg.type === "token") {
          const chunk: string = msg.text ?? "";
          if (!chunk) return;
          setMessages((prev) => prev.map((m) => (m.id === asstId ? { ...m, text: (m.text || "") + chunk } : m)));
          return;
        }
        if (msg.type === "done") {
          es.close();
          setBusy(false);
          return;
        }
        if (msg.type === "error") {
          setMessages((prev) => prev.map((m) => (m.id === asstId ? { ...m, text: (m.text || "") + `\n[Error: ${msg.message}]` } : m)));
          es.close();
          setBusy(false);
        }
      } catch {
        // ignore
      }
    };
    es.onerror = () => {
      es.close();
      setBusy(false);
      setMessages((prev) => prev.map((m) => (m.id === asstId ? { ...m, text: (m.text || "") + "\n[Stream disconnected]" } : m)));
    };
  };

  const clear = () => {
    setMessages([]);
    setInput("");
  };

  return (
    <div style={styles.app}>
      <div style={styles.header}>
        <h2 style={{ margin: 0 }}>Chatbot RAG (streaming)</h2>
        <button onClick={() => toggleTheme()} style={styles.themeBtn} title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}>
          {theme === "dark" ? "☀️ Light" : "🌙 Dark"}
        </button>
      </div>

      <div style={styles.scroll}>
        {messages.map((m) => (
          <Bubble key={m.id} role={m.role} text={m.text} sources={m.sources} />
        ))}
        <div ref={endRef} />
      </div>

      <div style={styles.inputRow}>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              ask();
            }
          }}
          placeholder="Ask me anything… (Enter to send, Shift+Enter for newline)"
          rows={3}
          style={styles.textarea}
        />
        <div style={{ display: "flex", gap: 8 }}>
          <button onClick={ask} disabled={busy || !input.trim()} style={styles.primaryBtn}>
            {busy ? "Thinking…" : "Send"}
          </button>
          <button onClick={clear} disabled={busy || messages.length === 0} style={styles.secondaryBtn}>
            Clear
          </button>
        </div>
      </div>
    </div>
  );
}

function Bubble({
  role,
  text,
  sources = [],
}: {
  role: "user" | "assistant";
  text: string;
  sources?: Source[];
}) {
  const isUser = role === "user";
  return (
    <div style={{ display: "flex", justifyContent: isUser ? "flex-end" : "flex-start", margin: "8px 0" }}>
      <div
        style={{
          maxWidth: 720,
          padding: "10px 12px",
          borderRadius: 12,
          whiteSpace: "pre-wrap",
          lineHeight: 1.5,
          background: isUser ? "var(--bubble-user)" : "var(--bubble-assistant)",
          border: `1px solid ${isUser ? "var(--bubble-user-brd)" : "var(--bubble-asst-brd)"}`,
          color: "var(--text)",
        }}
      >
        {text || (isUser ? "" : "…")}
        {sources.length > 0 && (
          <div style={{ marginTop: 8, display: "flex", gap: 6, flexWrap: "wrap" }}>
            {sources.map((s) =>
              s.href ? (
                <a
                  key={s.id}
                  href={s.href}
                  target="_blank"
                  rel="noreferrer"
                  title={s.preview || ""}
                  style={styles.sourceLink}
                >
                  [{s.id}] {s.source}
                </a>
              ) : (
                <span key={s.id} title={s.preview || ""} style={styles.sourceChip}>
                  [{s.id}] {s.source}
                </span>
              )
            )}
          </div>
        )}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  app: {
    maxWidth: 900,
    margin: "24px auto",
    padding: 16,
    fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif",
    background: "var(--bg)",
    color: "var(--text)",
    minHeight: "100vh",
  },
  header: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 8,
  },
  scroll: {
    height: "60vh",
    overflowY: "auto",
    padding: 8,
    border: "1px solid var(--border)",
    borderRadius: 10,
    background: "var(--panel)",
  },
  inputRow: {
    display: "grid",
    gridTemplateColumns: "1fr auto",
    gap: 10,
    marginTop: 10,
  },
  textarea: {
    width: "100%",
    padding: 10,
    borderRadius: 8,
    border: "1px solid var(--border)",
    background: "var(--panel)",
    color: "var(--text)",
    font: "inherit",
  },
  primaryBtn: {
    padding: "10px 14px",
    borderRadius: 8,
    border: "1px solid var(--primary)",
    background: "var(--primary)",
    color: "var(--primary-contrast)",
    cursor: "pointer",
  },
  secondaryBtn: {
    padding: "10px 14px",
    borderRadius: 8,
    border: "1px solid var(--border)",
    background: "var(--panel)",
    color: "var(--text)",
    cursor: "pointer",
  },
  themeBtn: {
    padding: "8px 12px",
    borderRadius: 8,
    border: "1px solid var(--border)",
    background: "var(--panel)",
    color: "var(--text)",
    cursor: "pointer",
  },
  sourceLink: {
    padding: "4px 8px",
    borderRadius: 8,
    background: "var(--chip-bg)",
    border: "1px solid var(--chip-brd)",
    color: "var(--chip-text)",
    textDecoration: "none",
    fontSize: 12,
  },
  sourceChip: {
    padding: "4px 8px",
    borderRadius: 8,
    background: "var(--chip-bg)",
    border: "1px solid var(--chip-brd)",
    color: "var(--chip-text)",
    fontSize: 12,
  },
};
