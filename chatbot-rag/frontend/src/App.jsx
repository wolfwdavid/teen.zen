// src/App.jsx
import React, { useEffect, useRef, useState } from "react";
import { Check, X, Clock } from "lucide-react";
import { API_BASE } from "./api/apiBase";

// ------------------------
// Small URL helper
// ------------------------
function joinUrl(base, path) {
  const b = String(base || "").trim().replace(/\/+$/, "");
  const p = String(path || "").trim().replace(/^\/+/, "");
  return `${b}/${p}`;
}

// ------------------------
// ChatMessage (Tailwind v4-friendly classes)
// ------------------------
function ChatMessage({ type, text, sources = [], timing, error }) {
  const isUser = type === "user";

  return (
    <div
      className={[
        "max-w-[90%] md:max-w-[75%] rounded-2xl px-4 py-3 shadow-sm ring-1 ring-white/10",
        "mb-3 flex flex-col gap-2",
        isUser ? "self-end bg-indigo-600 text-white" : "self-start bg-zinc-900/70 text-zinc-100",
      ].join(" ")}
    >
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs font-semibold tracking-wide opacity-90">
          {isUser ? "You" : "RAG Chatbot"}
        </p>
      </div>

      {error ? (
        <div className="inline-flex items-center gap-2 rounded-xl bg-red-500/10 px-3 py-2 text-sm text-red-200 ring-1 ring-red-500/20">
          <X className="h-4 w-4" />
          <span className="font-medium">Error:</span>
          <span className="break-words">{error}</span>
        </div>
      ) : (
        <div className="whitespace-pre-wrap break-words text-sm leading-relaxed">{text}</div>
      )}

      {!!timing && (
        <div className="mt-1 inline-flex items-center gap-2 border-t border-white/10 pt-2 text-xs text-zinc-300">
          <Clock className="h-3.5 w-3.5 text-amber-300" />
          <span>Response time:</span>
          <span className="font-semibold text-amber-300">{timing}s</span>
        </div>
      )}

      {Array.isArray(sources) && sources.length > 0 && (
        <div className="mt-2 border-t border-white/10 pt-2">
          <p className="mb-2 text-xs font-semibold text-zinc-300">Sources</p>

          <div className="flex flex-wrap gap-2">
            {sources.map((s, i) => {
              const href = s?.href;
              const label = s?.source || "source";
              const preview = s?.preview || "";

              const pill = (
                <span
                  className="inline-flex max-w-full items-center gap-2 rounded-full bg-indigo-500/10 px-3 py-1 text-xs text-indigo-200 ring-1 ring-indigo-500/20"
                  title={preview}
                >
                  <span className="opacity-80">[{i + 1}]</span>
                  <span className="truncate">{label}</span>
                </span>
              );

              return href ? (
                <a
                  key={i}
                  href={href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:opacity-90"
                >
                  {pill}
                </a>
              ) : (
                <span key={i}>{pill}</span>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

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
function ChatBoxStreamComponent({ debugMode }) {
  const [messages, setMessages] = useState(initialMessages);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [streamError, setStreamError] = useState(null);
  const messagesEndRef = useRef(null);

  const streamAbortRef = useRef(null);

  const scrollToBottom = () => messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
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

  const parseSseFrameToJson = (frame) => {
    if (!frame) return null;
    if (frame.startsWith(":")) return null;

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

    stop();

    // Add user message
    setMessages((prev) => [
      ...prev,
      { type: "user", text: userQuery, sources: [], timing: null, error: null },
    ]);

    // Add empty bot message immediately
    let chatbotIndex = -1;
    setMessages((prev) => {
      const next = [...prev, { type: "chatbot", text: "", sources: [], timing: null, error: null }];
      chatbotIndex = next.length - 1;
      return next;
    });

    const ac = new AbortController();
    streamAbortRef.current = ac;

    const apiUrl =
      joinUrl(API_BASE, "/chat/stream") + `?q=${encodeURIComponent(userQuery)}&heartbeat=2`;

    try {
      const response = await fetch(apiUrl, {
        method: "GET",
        headers: { Accept: "text/event-stream", "Cache-Control": "no-cache" },
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
            const idx = chatbotIndex >= 0 ? chatbotIndex : Math.max(0, next.length - 1);
            const cur =
              next[idx] ?? { type: "chatbot", text: "", sources: [], timing: null, error: null };

            if (data.type === "token") {
              gotAnyToken = true;
              next[idx] = { ...cur, text: (cur.text || "") + (data.text ?? "") };
            } else if (data.type === "sources") {
              next[idx] = { ...cur, sources: Array.isArray(data.items) ? data.items : [] };
            } else if (data.type === "perf_time") {
              next[idx] = { ...cur, timing: data.data ?? null };
            } else if (data.type === "error") {
              next[idx] = { ...cur, error: data.error ?? data.message ?? "Unknown error" };
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

      if (!gotAnyToken) {
        setStreamError(
          `SSE closed before any tokens. Open ${joinUrl(API_BASE, "/chat/stream")} in emulator Chrome to confirm it streams.`
        );
      }
    } catch (error) {
      if (error?.name !== "AbortError") {
        const errorMessage = `Connection Error: ${error?.message ?? String(error)}`;
        setStreamError(errorMessage);

        setMessages((prev) => {
          const next = [...prev];
          const idx = chatbotIndex >= 0 ? chatbotIndex : Math.max(0, next.length - 1);
          const cur = next[idx] ?? { type: "chatbot", text: "", sources: [], timing: null, error: null };
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
    <div className="mt-6 flex h-[70vh] flex-col overflow-hidden rounded-3xl bg-zinc-950/60 p-5 shadow-2xl ring-1 ring-white/10 backdrop-blur">
      {/* history */}
      <div className="flex-1 space-y-3 overflow-y-auto pr-2">
        {messages.map((m, i) => (
          <ChatMessage
            key={i}
            type={m.type}
            text={m.text}
            sources={m.sources}
            timing={m.timing}
            error={m.error}
          />
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* composer */}
      <form onSubmit={handleSubmit} className="mt-4 flex gap-2">
        <div className="relative flex-1">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isLoading || debugMode}
            placeholder={
              isLoading
                ? "Generating response…"
                : debugMode
                ? "Debugging in progress…"
                : "Ask your question…"
            }
            className="w-full rounded-2xl border border-white/10 bg-zinc-900/70 px-4 py-3 text-sm text-zinc-100 placeholder:text-zinc-400 outline-none ring-0 focus:border-indigo-500/40 focus:ring-4 focus:ring-indigo-500/10"
          />
        </div>

        <button
          type="submit"
          disabled={isLoading || debugMode}
          className={[
            "inline-flex items-center justify-center rounded-2xl px-4 py-3 text-sm font-semibold",
            "shadow-sm ring-1 ring-white/10 transition",
            isLoading || debugMode
              ? "cursor-not-allowed bg-zinc-800 text-zinc-400"
              : "bg-indigo-600 text-white hover:bg-indigo-500",
          ].join(" ")}
        >
          {isLoading ? "…" : "Send"}
        </button>

        <button
          type="button"
          onClick={stop}
          disabled={!isLoading}
          className={[
            "inline-flex items-center justify-center rounded-2xl px-4 py-3 text-sm font-semibold",
            "ring-1 ring-white/10 transition",
            !isLoading
              ? "cursor-not-allowed bg-zinc-900/50 text-zinc-500"
              : "bg-zinc-800 text-zinc-100 hover:bg-zinc-700",
          ].join(" ")}
        >
          Stop
        </button>
      </form>

      {streamError && (
        <div className="mt-3 rounded-2xl bg-red-500/10 p-3 text-sm text-red-200 ring-1 ring-red-500/20">
          <div className="flex items-start gap-2">
            <X className="mt-0.5 h-4 w-4" />
            <div className="min-w-0">
              <div className="font-semibold">Streaming error</div>
              <div className="break-words">{streamError}</div>
              <div className="mt-2 text-xs text-red-200/80">
                API_BASE=<span className="font-mono">{String(API_BASE)}</span>
              </div>
              <div className="text-xs text-red-200/80">
                Try emulator Chrome:{" "}
                <span className="font-mono">{joinUrl(API_BASE, "/health")}</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ------------------------
// App
// ------------------------
export default function App() {
  const [debugMode, setDebugMode] = useState(false);
  const [msg, setMsg] = useState("Ready");
  const [raw, setRaw] = useState("");
  const [backend, setBackend] = useState({ status: "checking", detail: "" });

  const isNative =
    typeof window !== "undefined" && (window?.Capacitor?.isNativePlatform?.() ?? false);

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
      setMsg("Fetch error");
      setRaw(String(e));
    }
  };

  useEffect(() => {
    let alive = true;
    const ac = new AbortController();

    const run = async () => {
      try {
        const url = joinUrl(API_BASE, "/health");
        const r = await fetch(url, { signal: ac.signal, headers: { Accept: "application/json" } });
        const j = await r.json().catch(() => null);
        if (!alive) return;

        if (r.ok && j?.ok) {
          const ready = !!j.initialized && !!j.model_loaded;
          setBackend({ status: "up", detail: ready ? "Model ready" : "Backend up (warming)" });
        } else {
          setBackend({ status: "down", detail: `HTTP ${r.status}` });
        }
      } catch (e) {
        if (!alive) return;
        setBackend({ status: "down", detail: e?.message ?? String(e) });
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

  const badge =
    backend.status === "up"
      ? { text: `Backend connected ✓ — ${backend.detail}`, cls: "bg-emerald-500/10 text-emerald-200 ring-emerald-500/20" }
      : backend.status === "down"
      ? { text: `Backend offline ✕ — ${backend.detail}`, cls: "bg-red-500/10 text-red-200 ring-red-500/20" }
      : { text: "Checking backend…", cls: "bg-zinc-500/10 text-zinc-200 ring-white/10" };

  return (
    <div className="min-h-screen bg-gradient-to-b from-zinc-950 via-zinc-950 to-black text-zinc-100">
      <div className="mx-auto w-full max-w-5xl px-4 py-8">
        <header className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="space-y-2">
            <h1 className="text-3xl font-semibold tracking-tight">
              {debugMode ? "RAG Chat – Debug" : "RAG Chatbot"}
            </h1>

            <div className="flex flex-wrap items-center gap-2">
              <span className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs ring-1 ${badge.cls}`}>
                {badge.text}
              </span>

              <span className="inline-flex items-center gap-2 rounded-full bg-white/5 px-3 py-1 text-xs text-zinc-300 ring-1 ring-white/10">
                API: <span className="font-mono">{String(API_BASE)}</span>
              </span>

              <span className="inline-flex items-center gap-2 rounded-full bg-white/5 px-3 py-1 text-xs text-zinc-300 ring-1 ring-white/10">
                Native: <span className="font-mono">{String(isNative)}</span>
              </span>
            </div>
          </div>

          <button
            onClick={() => setDebugMode((d) => !d)}
            className="inline-flex items-center justify-center rounded-2xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm ring-1 ring-white/10 transition hover:bg-indigo-500"
          >
            {debugMode ? "💬 Chat Mode" : "🧠 Debug Mode"}
          </button>
        </header>

        {debugMode ? (
          <div className="mt-6 rounded-3xl bg-zinc-950/60 p-5 shadow-2xl ring-1 ring-white/10 backdrop-blur">
            <button
              type="button"
              onClick={ping}
              className="inline-flex items-center justify-center rounded-2xl bg-emerald-600 px-4 py-2 text-sm font-semibold text-white shadow-sm ring-1 ring-white/10 transition hover:bg-emerald-500"
            >
              <Check className="mr-2 h-4 w-4" />
              Ping Backend /health
            </button>

            <div className="mt-4 text-sm text-zinc-200">
              <span className="font-semibold text-emerald-200">Status:</span> {msg}
            </div>

            {raw && (
              <pre className="mt-4 overflow-x-auto rounded-2xl bg-black/60 p-4 text-xs text-emerald-200 ring-1 ring-white/10">
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
