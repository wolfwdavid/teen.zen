// Define the response type
export type ChatReply = {
  answer: string;
  sources: {
    id: number;
    source: string;
    href?: string;
    preview?: string;
  }[];
};

// Fetch helper
export async function askChatbot(question: string): Promise<ChatReply> {
  const res = await fetch("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });

  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}
