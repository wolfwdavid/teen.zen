import { useState } from "react";

export default function ChatApp() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");

  async function sendMessage() {
    if (!input.trim()) return;

    // 👇 Notice we call "/chat" instead of "http://localhost:8000/chat"
    const res = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: input }),
    });

    const data = await res.json();

    setMessages((prev) => [
      ...prev,
      { role: "user", text: input },
      { role: "bot", text: data.answer },
    ]);

    setInput("");
  }

  return (
    <div className="chat-container">
      <div className="chat-box">
        {messages.map((m, i) => (
          <div key={i} className={`msg ${m.role}`}>
            {m.text}
          </div>
        ))}
      </div>
      <div className="chat-input">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && sendMessage()}
          placeholder="Type your question..."
        />
        <button onClick={sendMessage}>Send</button>
      </div>
    </div>
  );
}
