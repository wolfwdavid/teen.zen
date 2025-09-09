export async function askChatbot(question) {
  const res = await fetch("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });

  if (!res.ok) {
    throw new Error(`Chat request failed: ${res.status}`);
  }
  return res.json();
}

