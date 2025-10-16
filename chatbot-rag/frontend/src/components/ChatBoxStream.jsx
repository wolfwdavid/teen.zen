import { useState } from "react";
import { useChatStreamTyping } from "../hooks/useChatStream";

export default function ChatBoxStream() {
  const [question, setQuestion] = useState("");
  const { text, open, error, start, stop } = useChatStreamTyping(30); // 30ms per word

  return (
    <div style={{ maxWidth: 720, margin: "2rem auto", fontFamily: "system-ui" }}>
      <h2>RAG Chat (Streaming + Typing)</h2>

      <textarea
        rows={4}
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        placeholder="Ask me anything…"
        style={{ width: "100%", padding: 12, borderRadius: 8 }}
      />

      <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
        <button onClick={() => start(question)} disabled={!question.trim() || open}>
          {open ? "Streaming…" : "Ask (SSE Typing)"}
        </button>
        <button onClick={stop} disabled={!open && !text}>Stop</button>
      </div>

      {error && (
        <pre style={{ marginTop: 12, color: "#b00020", whiteSpace: "pre-wrap" }}>
          Error: {error}
        </pre>
      )}

      <div style={{
        marginTop: 12, padding: 12, background: "#0b1020", color: "#e6edf3",
        borderRadius: 8, minHeight: 100, fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
        whiteSpace: "pre-wrap", lineHeight: 1.5, position: "relative"
      }}>
        {text}
        {/* caret */}
        <span className="caret" style={{
          display: "inline-block",
          width: 8, height: 16, marginLeft: 2,
          background: "#e6edf3",
          verticalAlign: "text-bottom",
          animation: "blink 1s step-end infinite"
        }} />
      </div>

      {/* simple blink keyframes */}
      <style>{`
        @keyframes blink { 50% { opacity: 0; } }
        button { padding: 8px 12px; border-radius: 8px; }
      `}</style>
    </div>
  );
}
