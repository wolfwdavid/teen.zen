// src/App.jsx
import { useState } from "react";
import ChatBoxStream from "./components/ChatBoxStream";

export default function App() {
  const [debugMode, setDebugMode] = useState(false);
  const [msg, setMsg] = useState("Ready");
  const [raw, setRaw] = useState("");

  const ping = async () => {
    setMsg("Pinging /health …");
    setRaw("");
    try {
      const r = await fetch("/health");
      const txt = await r.text();
      setMsg(`/health → HTTP ${r.status}`);
      setRaw(txt);
    } catch (e) {
      console.error("[debug] fetch error:", e);
      setMsg("Fetch error");
      setRaw(String(e));
    }
  };

  return (
    <div
      style={{
        maxWidth: 720,
        margin: "2rem auto",
        fontFamily: "system-ui",
        color: "#111",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h1>{debugMode ? "RAG Chat – Debug" : "RAG Chatbot"}</h1>
        <button
          onClick={() => setDebugMode((d) => !d)}
          style={{
            padding: "6px 12px",
            fontSize: 14,
            background: "#eef2ff",
            border: "1px solid #c7d2fe",
            borderRadius: 6,
            cursor: "pointer",
          }}
        >
          {debugMode ? "💬 Chat Mode" : "🧠 Debug Mode"}
        </button>
      </div>

      {debugMode ? (
        <div>
          <button type="button" onClick={ping} style={{ padding: "8px 16px" }}>
            Ping Backend
          </button>
          <div style={{ marginTop: 12 }}>
            <strong>Status:</strong> {msg}
          </div>
          {raw && (
            <pre
              style={{
                marginTop: 12,
                background: "#f6f6f6",
                padding: 12,
                borderRadius: 8,
                whiteSpace: "pre-wrap",
              }}
            >
              {raw}
            </pre>
          )}
        </div>
      ) : (
        <ChatBoxStream />
      )}
    </div>
  );
}
