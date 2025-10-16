import { useState } from "react";
import ChatBoxStream from "./components/ChatBoxStream";

export default function App() {
  return <ChatBoxStream />;
}


export default function App() {
  const [msg, setMsg] = useState("Ready");
  const [raw, setRaw] = useState("");

  const ping = async () => {
    console.log("[debug] button clicked");
    setMsg("Pinging /health …");
    setRaw("");
    try {
      // Try via Vite proxy first:
      const r = await fetch("/health");
      console.log("[debug] /health status:", r.status);
      const txt = await r.text();
      console.log("[debug] /health body:", txt);
      setMsg(`/health → HTTP ${r.status}`);
      setRaw(txt);
    } catch (e) {
      console.error("[debug] fetch error:", e);
      setMsg("Fetch error");
      setRaw(String(e));
    }
  };

  return (
    <div style={{ maxWidth: 720, margin: "2rem auto", fontFamily: "system-ui" }}>
      <h1>RAG Chat – Debug</h1>
      <button type="button" onClick={ping} style={{ padding: "8px 16px" }}>
        Ping Backend
      </button>
      <div style={{ marginTop: 12 }}>
        <strong>Status:</strong> {msg}
      </div>
      {raw && (
        <pre style={{ marginTop: 12, background: "#f6f6f6", padding: 12, borderRadius: 8, whiteSpace: "pre-wrap" }}>
          {raw}
        </pre>
      )}
    </div>
  );
}
