import { useState } from "react";
import { askChatbot } from "../api/chat"; // adjust path if needed

export default function ChatBox() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  const handleAsk = async () => {
    if (!question.trim()) return;
    setLoading(true);
    setAnswer("");
    setSources([]);
    try {
      const data = await askChatbot(question);
      setAnswer(data.answer || "");
      setSources(Array.isArray(data.sources) ? data.sources : []);
    } catch (err: any) {
      setAnswer("Error: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div 
     className="chat-box" 
     style={{ maxWidth: 700, margin: "40px auto", padding: 16 }}
    >
      <textarea
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleAsk();
          }
        }}
        placeholder="Ask me anything..."
        rows={4}
        style={{ width: "100%", padding: 8 }}
      />

      <button
        onClick={handleAsk}
        disabled={loading || !question.trim()}
        style={{ marginTop: 8 }}
      >
        {loading ? "Thinking..." : "Ask"}
      </button>

      {answer && (
        <div style={{ marginTop: 12, whiteSpace: "pre-wrap", lineHeight: 1.5 }}>
          <strong>Answer:</strong> {answer}
        </div>
      )}

      {/* 🧠 Citation chips */}
      {sources.length > 0 && (
        <div style={{ marginTop: 12, display: "flex", flexWrap: "wrap", gap: 8 }}>
          {sources.map((s, i) => {
            const label = `[${i + 1}] ${s.source || "source"}`;
            return s.href ? (
              <a
                key={i}
                href={s.href}
                target="_blank"
                rel="noreferrer"
                title={s.preview || ""}
                style={{
                  padding: "6px 10px",
                  borderRadius: 8,
                  background: "#eef2ff",
                  border: "1px solid #c7d2fe",
                  textDecoration: "none",
                  color: "#1d4ed8",
                }}
              >
                {label}
              </a>
            ) : (
              <div
                key={i}
                title={s.preview || ""}
                style={{
                  padding: "6px 10px",
                  borderRadius: 8,
                  background: "#eef2ff",
                  border: "1px solid #c7d2fe",
                }}
              >
                {label}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
