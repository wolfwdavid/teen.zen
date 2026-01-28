import React, { useEffect, useRef, useState } from "react";
import { Check, X, Clock } from "lucide-react";
import { API_BASE } from "./api/apiBase";

<span className="opacity-70">
  Native: {String(window?.Capacitor?.isNativePlatform?.() ?? false)}
</span>
// ------------------------
// Small URL helper
// ------------------------
function joinUrl(base, path) {
  const b = String(base || "").trim().replace(/\/+$/, "");
  const p = String(path || "").trim().replace(/^\/+/, "");
  return `${b}/${p}`;
}

// ------------------------
// ChatMessage
// ------------------------
const ChatMessage = ({ type, text, sources = [], timing, error }) => {
  const isUser = type === "user";
  const bgColor = isUser
    ? "bg-indigo-600 text-white"
    : "bg-gray-700 text-gray-100";
  const alignment = isUser
    ? "self-end items-end"
    : "self-start items-start";

  return (
    <div
      className={`max-w-[90%] md:max-w-[75%] p-4 rounded-xl shadow-lg mb-4 flex flex-col ${bgColor} ${alignment}`}
    >
      <p className="font-semibold mb-1 text-sm">
        {isUser ? "You" : "RAG Chatbot"}:
      </p>

      {error ? (
        <div className="text-red-300 font-medium">
          <X className="inline w-4 h-4 mr-1" /> Error: {error}
        </div>
      ) : (
        <div className="whitespace-pre-wrap text-left">{text}</div>
      )}

      {!!timing && (
        <div className="mt-3 pt-2 border-t border-gray-600 text-xs text-gray-400 flex items-center">
          <Clock className="w-3 h-3 mr-1 text-yellow-300" />
          Response Time:{" "}
          <span className="font-bold text-yellow-300 ml-1">
            {timing} seconds
          </span>
        </div>
      )}

      {Array.isArray(sources) && sources.length > 0 && (
        <div className="mt-3 pt-2 border-t border-gray-600 text-xs text-gray-400 text-left">
          <p className="font-bold mb-1">Sources:</p>
          {sources.map((source, index) => {
            const href = source?.href;
            const label = source?.source || "source";
            const preview = source?.preview || "";

            return (
              <span key={index} className="block italic leading-tight">
                [{index + 1}]{" "}
                {href ? (
                  <a
                    href={href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:underline text-indigo-300"
                  >
                    {label}
                  </a>
                ) : (
                  <span className="text-indigo-200">{label}</span>
                )}
                {preview ? (
                  <p className="text-[10px] truncate">{preview}</p>
                ) : null}
              </span>
            );
          })}
        </div>
      )}
    </div>
  );
};

// ------------------------
// Initial messages
// ------------------------
const initialMessages = [
  {
    type: "chatbot",
    text: "Hello! I am ready to answer questions based on my context documents.",
    sources: [],
    timing: null,
    error: null,
  },
];

// ------------------------
// Chat component (SSE via fetch streaming)
// ------------------------
const ChatBoxStreamComponent = ({ debugMode }) => {
  const [messages, setMessages] = useState(initialMessages);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [streamError, setStreamError] = useState(null);
  const messagesEndRef = useRef(null);

  // Cancel stream
  const streamAbortRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };
  useEffect(scrollToBottom, [messages]);

  const stop = () => {
    setIsLoading(false);
    if (streamAbortRef.current) {
      try {
        streamAbortRef.current.abort();
      } catch {}
      streamAbortRef.current = null;
    }
  };

  // Parse one SSE frame into JSON (supports multiple data: lines)
  const parseSseFrameToJson = (frame) => {
    if (!frame) return null;
    if (frame.startsWith(":")) return null; // heartbeat/comment

    const dataLines = frame
      .split("\n")
      .filter((l) => l.startsWith("data:"))
      .map((l) => l.replace(/^data:\s*/, ""));

    if (!dataLines.length) return null;

    const payload = dataLines.join("\n").trim();
    if (!payload) return null;

    try {
      return JSON.parse(payload);
    } catch {
      return null;
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading || debugMode) return;

    const userQuery = input.trim();
    setInput("");
    setIsLoading(true);
    setStreamError(null);

    // stop any prior stream
    stop();

    // Add user message
    setMessages((prev) => [
      ...prev,
      { type: "user", text: userQuery, sources: [], timing: null, error: null },
    ]);

    // Add an empty chatbot message immediately so updates always target it
    let chatbotIndex = -1;
    setMessages((prev) => {
      const next = [
        ...prev,
        { type: "chatbot", text: "", sources: [], timing: null, error: null },
      ];
      chatbotIndex = next.length - 1;
      return next;
    });

    // Abort controller for this stream
    const ac = new AbortController();
    streamAbortRef.current = ac;

    const apiUrl =
      joinUrl(API_BASE, "/chat/stream") +
      `?q=${encodeURIComponent(userQuery)}&heartbeat=2`;

    try {
      const response = await fetch(apiUrl, {
        method: "GET",
        headers: {
          Accept: "text/event-stream",
          "Cache-Control": "no-cache",
        },
        signal: ac.signal,
      });

      if (!response.ok || !response.body) {
        const errorText = await response.text().catch(() => "");
        throw new Error(`HTTP ${response.status}: ${errorText || "Server Error"}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");

      let buffer = "";
      let gotAnyToken = false;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        const frames = buffer.split("\n\n");
        buffer = frames.pop() ?? "";

        for (const frame of frames) {
          const data = parseSseFrameToJson(frame);
          if (!data) continue;

          setMessages((prev) => {
            const next = [...prev];
            const idx =
              chatbotIndex >= 0 ? chatbotIndex : Math.max(0, next.length - 1);

            const cur = next[idx] ?? {
              type: "chatbot",
              text: "",
              sources: [],
              timing: null,
              error: null,
            };

            // backend emits: sources/token/perf_time/done
            if (data.type === "token") {
              gotAnyToken = true;
              next[idx] = { ...cur, text: (cur.text || "") + (data.text ?? "") };
            } else if (data.type === "sources") {
              next[idx] = {
                ...cur,
                sources: Array.isArray(data.items) ? data.items : [],
              };
            } else if (data.type === "perf_time") {
              next[idx] = { ...cur, timing: data.data ?? null };
            } else if (data.type === "error") {
              next[idx] = {
                ...cur,
                error: data.error ?? data.message ?? "Unknown error",
              };
            } else if (data.type === "done") {
              // nothing special; stream will end naturally
            }

            return next;
          });

          if (data.type === "done") {
            try {
              await reader.cancel();
            } catch {}
            break;
          }
        }
      }

      // If the stream closed before any tokens arrived, show a clearer hint
      if (!gotAnyToken) {
        setStreamError(
          `SSE closed before any tokens. Try opening ${joinUrl(
            API_BASE,
            "/chat/stream"
          )} in emulator Chrome to confirm it streams.`
        );
      }
    } catch (error) {
      if (error?.name === "AbortError") {
        // user pressed Stop; keep partial text
      } else {
        const errorMessage = `Connection Error: ${error?.message ?? String(error)}`;
        setStreamError(errorMessage);

        setMessages((prev) => {
          const next = [...prev];
          const idx =
            chatbotIndex >= 0 ? chatbotIndex : Math.max(0, next.length - 1);
          const cur = next[idx];
          next[idx] = { ...cur, error: errorMessage };
          return next;
        });
      }
    } finally {
      setIsLoading(false);
      streamAbortRef.current = null;
    }
  };

  return (
    <div className="flex flex-col h-[70vh] bg-gray-800 p-6 rounded-xl shadow-2xl mt-4">
      <div className="flex-grow overflow-y-auto mb-4 space-y-4 pr-3">
        {messages.map((msg, index) => (
          <ChatMessage
            key={index}
            type={msg.type}
            text={msg.text}
            sources={msg.sources}
            timing={msg.timing}
            error={msg.error}
          />
        ))}
        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSubmit} className="flex space-x-3">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={
            isLoading
              ? "Generating response..."
              : debugMode
              ? "Debugging in progress..."
              : "Ask your question..."
          }
          disabled={isLoading || debugMode}
          className="flex-grow p-3 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition duration-150"
        />

        <button
          type="submit"
          disabled={isLoading || debugMode}
          className={`p-3 rounded-lg font-semibold transition duration-150 flex items-center justify-center ${
            isLoading || debugMode
              ? "bg-gray-500 cursor-not-allowed"
              : "bg-indigo-600 hover:bg-indigo-700 shadow-md"
          } w-24`}
        >
          {isLoading ? "…" : "Send"}
        </button>

        <button
          type="button"
          onClick={stop}
          disabled={!isLoading}
          className={`p-3 rounded-lg font-semibold transition duration-150 flex items-center justify-center ${
            !isLoading
              ? "bg-gray-700 cursor-not-allowed opacity-60"
              : "bg-gray-600 hover:bg-gray-500"
          } w-24`}
        >
          Stop
        </button>
      </form>

      {streamError && (
        <div className="mt-4 text-center text-red-400 text-sm p-2 bg-red-900/30 rounded-lg">
          <X className="inline w-4 h-4 mr-1" /> {streamError}
          <div className="mt-1 text-xs opacity-80">
            API_BASE=<span className="font-mono">{String(API_BASE)}</span>
          </div>
          <div className="mt-1 text-xs opacity-80">
            Try emulator Chrome:{" "}
            <span className="font-mono">{joinUrl(API_BASE, "/health")}</span>
          </div>
        </div>
      )}
    </div>
  );
};

// ------------------------
// App: backend badge + debug ping using API_BASE
// ------------------------
export default function App() {
  const [debugMode, setDebugMode] = useState(false);

  const [msg, setMsg] = useState("Ready");
  const [raw, setRaw] = useState("");

  const [backend, setBackend] = useState({
    status: "checking",
    detail: "",
  });

  const ping = async () => {
    setMsg("Pinging /health …");
    setRaw("");
    try {
      const url = joinUrl(API_BASE, "/health");
      const r = await fetch(url, { headers: { Accept: "application/json" } });
      const txt = await r.text();
      setMsg(`/health → HTTP ${r.status}`);
      setRaw(txt);
    } catch (e) {
      console.error("[debug] fetch error:", e);
      setMsg("Fetch error");
      setRaw(String(e));
    }
  };

  // Auto health ping (badge)
  useEffect(() => {
    let alive = true;
    const ac = new AbortController();

    const run = async () => {
      try {
        const url = joinUrl(API_BASE, "/health");
        const r = await fetch(url, {
          signal: ac.signal,
          headers: { Accept: "application/json" },
        });

        const j = await r.json().catch(() => null);
        if (!alive) return;

        if (r.ok && j?.ok) {
          const ready = !!j.initialized && !!j.model_loaded;
          setBackend({
            status: "up",
            detail: ready ? "Model ready" : "Backend up (warming)",
          });
        } else {
          setBackend({
            status: "down",
            detail: `HTTP ${r.status}`,
          });
        }
      } catch (e) {
        if (!alive) return;
        setBackend({
          status: "down",
          detail: e?.message ?? String(e),
        });
      }
    };

    run();
    const t = setInterval(run, 10000);

    return () => {
      alive = false;
      clearInterval(t);
      ac.abort();
    };
  }, []);

  const badgeText =
    backend.status === "up"
      ? `Backend connected ✅ — ${backend.detail}`
      : backend.status === "down"
      ? `Backend offline ❌ — ${backend.detail}`
      : "Checking backend…";

  const badgeBg =
    backend.status === "up"
      ? "bg-green-900/30 border-green-700 text-green-200"
      : backend.status === "down"
      ? "bg-red-900/30 border-red-700 text-red-200"
      : "bg-gray-800 border-gray-700 text-gray-200";

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100 flex flex-col items-center p-4">
      <div className="w-full max-w-3xl">
        <header className="flex justify-between items-center mb-6 py-4 border-b border-gray-700">
          <div className="flex flex-col gap-2">
            <h1 className="text-3xl font-bold text-indigo-400">
              {debugMode ? "RAG Chat – Debug" : "RAG Chatbot"}
            </h1>

            <div
              className={`inline-flex items-center gap-2 text-xs px-3 py-1 rounded-full border ${badgeBg}`}
            >
              <span>{badgeText}</span>
              <span className="opacity-70">API: {String(API_BASE)}</span>
            </div>
          </div>

          <button
            onClick={() => setDebugMode((d) => !d)}
            className="p-2 px-4 text-sm font-medium bg-indigo-900/50 hover:bg-indigo-900 border border-indigo-700 text-indigo-300 rounded-lg transition duration-150 shadow-md"
          >
            {debugMode ? "💬 Chat Mode" : "🧠 Debug Mode"}
          </button>
        </header>

        {debugMode ? (
          <div className="bg-gray-800 p-6 rounded-xl shadow-2xl">
            <button
              type="button"
              onClick={ping}
              className="p-2 px-4 bg-teal-600 hover:bg-teal-700 rounded-lg font-semibold transition duration-150"
            >
              <Check className="inline w-4 h-4 mr-2" /> Ping Backend /health
            </button>

            <div className="mt-4 text-sm">
              <strong className="text-teal-400">Status:</strong> {msg}
            </div>

            {raw && (
              <pre className="mt-4 bg-gray-900 text-green-300 p-4 rounded-lg overflow-x-auto text-xs">
                {raw}
              </pre>
            )}
          </div>
        ) : (
          <ChatBoxStreamComponent debugMode={debugMode} />
        )}
      </div>
    </div>
  );
}
