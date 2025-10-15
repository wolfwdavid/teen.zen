import { useState } from "react";

async function askChatbot(question) {
  console.log("[chat] sending:", question);
  const res = await fetch("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`HTTP ${res.status} ${res.statusText} – ${text}`);
  }
  return res.json();
}

export default function ChatBox() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleAsk = async () => {
    if (!question.trim()) return;
    setLoading(true);
    setError("");
    setAnswer("");
    try {
      const data = await askChatbot(question.trim());
      console.log("[chat] response:", data);
      setAnswer(data.answer ?? "(no answer field)");
    } catch (err) {
      console.error("[chat] error:", err);
      setError(String(err.message || err));
    } finally {
      setLoading(false);
    }
  };

  const onKeyDown = (e) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handleAsk();
  };

  return (
    <div style={{ maxWidth: 720, margin: "2rem auto", fontFamily: "system-ui" }}>
      <h2>RAG Chat</h2>
      <textarea
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        onKeyDown={onKeyDown}
        placeholder="Ask me anything…"
        rows={5}
        style={{ width: "100%", padding: 12 }}
      />
      <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
        <button
          type="button"
          onClick={handleAsk}
          disabled={loading || !question.trim()}
          style={{ padding: "8px 16px" }}
        >
          {loading ? "Thinking…" : "Send"}
        </button>
        <span style={{ opacity: 0.6 }}>{loading ? "working…" : ""}</span>
      </div>

      {error && (
        <pre style={{ marginTop: 16, color: "#b00020", whiteSpace: "pre-wrap" }}>
          Error: {error}
        </pre>
      )}
      {answer && !error && (
        <div style={{ marginTop: 16, padding: 12, background: "#f6f6f6", borderRadius: 8 }}>
          <strong>Answer:</strong>
          <div style={{ marginTop: 8, whiteSpace: "pre-wrap" }}>{answer}</div>
        </div>
      )}
    </div>
  );
}
