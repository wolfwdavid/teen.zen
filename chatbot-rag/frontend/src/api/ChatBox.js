import { useState } from "react";
import { askChatbot } from "../api/chat";  // adjust path if needed

export default function ChatBox() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);

  const handleAsk = async () => {
    setLoading(true);
    setAnswer("");
    try {
      const data = await askChatbot(question);
      setAnswer(data.answer);
    } catch (err) {
      setAnswer("Error: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="chat-box">
      <textarea
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        placeholder="Ask me anything..."
      />
      <button onClick={handleAsk} disabled={loading || !question}>
        {loading ? "Thinking..." : "Ask"}
      </button>
      {answer && (
        <div className="answer">
          <strong>Answer:</strong> {answer}
        </div>
      )}
    </div>
  );
}
