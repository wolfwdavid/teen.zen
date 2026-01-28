import { API_BASE } from "./apiBase";

export async function askChatbot(question: string) {
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });

  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}
