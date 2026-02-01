import { useEffect, useRef, useState } from "react";

/**
 * Streams tokens via SSE and reveals them with a typewriter effect.
 * - speed: ms between words (default 30)
 */
export function useChatStreamTyping(speed = 30) {
  const [visibleText, setVisibleText] = useState("");
  const [rawBuffer, setRawBuffer] = useState("");    // raw streamed tokens
  const [open, setOpen] = useState(false);
  const [error, setError] = useState("");
  const esRef = useRef(null);
  const timerRef = useRef(null);

  // Start SSE
  const start = (question) => {
    if (!question?.trim()) return;
    stop();
    setVisibleText("");
    setRawBuffer("");
    setError("");

    const url = `/api/chat/stream?question=${encodeURIComponent(question)}`;
    const es = new EventSource(url);
    esRef.current = es;
    setOpen(true);

    es.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg.type === "token") {
          setRawBuffer((prev) => prev + msg.text); // accumulate raw tokens
        } else if (msg.type === "done") {
          closeStream(); // keep typing out remaining buffer
        } else if (msg.type === "error") {
          setError(msg.message || "Unknown error");
          closeStream();
        }
      } catch {
        // non-JSON line: just append
        setRawBuffer((prev) => prev + ev.data);
      }
    };

    es.onerror = () => {
      setError("Stream error or connection closed.");
      closeStream();
    };
  };

  const closeStream = () => {
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }
    setOpen(false);
  };

  // Typewriter: reveal rawBuffer word-by-word at a steady pace
  useEffect(() => {
    if (timerRef.current) clearInterval(timerRef.current);

    timerRef.current = setInterval(() => {
      setRawBuffer((buf) => {
        if (!buf) return buf;

        // Split off the next "word" (or token) + following space/newline if present
        // This keeps punctuation tight and feels natural.
        const match = buf.match(/^\s*\S+[\s\n]?/);
        if (!match) {
          // If we don't see a word boundary yet, reveal a single char to avoid stalls
          setVisibleText((t) => t + buf[0]);
          return buf.slice(1);
        }
        const nextChunk = match[0];
        setVisibleText((t) => t + nextChunk);
        return buf.slice(nextChunk.length);
      });
    }, speed);

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [speed]);

  const stop = () => {
    closeStream();
    if (timerRef.current) clearInterval(timerRef.current);
  };

  return { text: visibleText, open, error, start, stop };
}
