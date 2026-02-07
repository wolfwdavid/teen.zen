import React, { useState, useEffect, useRef } from 'react';
import { 
  Check, 
  X, 
  Clock, 
  Bot, 
  User, 
  Send, 
  StopCircle, 
  MessageSquare,
  ShieldCheck,
  Globe,
  Terminal,
  UserPlus,
  ShieldAlert,
  Eye,
  EyeOff
} from 'lucide-react';

// --- Configuration ---
import API_BASE from "./api/apiBase";

// --- Helpers ---
function joinUrl(base, path) {
  const b = String(base || "").trim().replace(/\/+$/, "");
  const p = String(path || "").trim().replace(/^\/+/, "");
  return `${b}/${p}`;
}

// --- Components ---

const ChatMessage = ({ type, text, sources = [], timing, error }) => {
  const isUser = type === 'user';
  
  return (
    <div className={`group flex w-full flex-col ${isUser ? 'items-end' : 'items-start'} mb-8 animate-in fade-in slide-in-from-bottom-2 duration-300`}>
      <div className={`flex max-w-[85%] gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
        <div className={`flex h-9 w-9 shrink-0 select-none items-center justify-center rounded-full border shadow-sm ${
          isUser ? 'bg-indigo-600 border-indigo-500 text-white' : 'bg-zinc-800 border-zinc-700 text-zinc-300'
        }`}>
          {isUser ? <User size={18} /> : <Bot size={18} />}
        </div>

        <div className={`relative flex flex-col gap-2 rounded-2xl px-4 py-3 text-sm shadow-sm ring-1 ${
          isUser 
            ? 'bg-indigo-600 text-white ring-indigo-500' 
            : 'bg-zinc-900/50 text-zinc-100 ring-zinc-800 backdrop-blur-sm'
        }`}>
          {error ? (
            <div className="flex items-center gap-2 text-red-300 font-medium">
              <ShieldAlert size={14} /> <span>{error}</span>
            </div>
          ) : (
            <div className="whitespace-pre-wrap leading-relaxed">{text || (isUser ? "" : "...")}</div>
          )}

          {timing && (
            <div className={`mt-1 flex items-center gap-1.5 text-[10px] uppercase tracking-wider font-bold border-t border-white/5 pt-2 ${isUser ? 'text-indigo-200' : 'text-zinc-500'}`}>
              <Clock size={12} className={isUser ? "text-indigo-200" : "text-amber-400"} />
              <span>{timing}s latency</span>
            </div>
          )}
        </div>
      </div>

      {!isUser && sources.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2 pl-12">
          {sources.map((s, i) => (
            <div 
              key={i} 
              title={s.preview}
              className="group/pill flex items-center gap-1.5 rounded-lg border border-zinc-800 bg-zinc-900/30 px-2.5 py-1 text-[11px] text-zinc-400 transition hover:bg-zinc-800 hover:text-zinc-200 cursor-help"
            >
              <span className="font-mono text-indigo-400">[{i + 1}]</span>
              <span className="max-w-[120px] truncate">{s.source}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default function App() {
  const [view, setView] = useState('chat'); // 'chat', 'register', 'debug'
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [streamError, setStreamError] = useState(null);
  const [backend, setBackend] = useState({ status: "checking", detail: "" });
  
  // Registration States
  const [showPassword, setShowPassword] = useState(false);
  const [role, setRole] = useState('user'); // 'user' or 'provider'

  const messagesEndRef = useRef(null);
  const streamAbortRef = useRef(null);

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Health check
  useEffect(() => {
    let alive = true;
    const ac = new AbortController();
    const checkStatus = async () => {
      try {
        const url = joinUrl(API_BASE, "/health");
        const r = await fetch(url, { 
          signal: ac.signal,
          headers: { 'ngrok-skip-browser-warning': 'true' }
        });
        const j = await r.json().catch(() => null);
        if (!alive) return;
        if (r.ok && j?.status === 'ok') {
          setBackend({ status: "up", detail: "Model Ready" });
        } else {
          setBackend({ status: "down", detail: `HTTP ${r.status}` });
        }
      } catch (e) {
        if (alive) setBackend({ status: "down", detail: "Offline" });
      }
    };
    checkStatus();
    const t = setInterval(checkStatus, 10000);
    return () => { alive = false; clearInterval(t); ac.abort(); };
  }, []);

  const handleStop = () => {
    setIsLoading(false);
    if (streamAbortRef.current) {
      try { streamAbortRef.current.abort(); } catch {}
      streamAbortRef.current = null;
    }
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userQuery = input.trim();
    setInput("");
    setIsLoading(true);
    setStreamError(null);

    // 1. Add user message
    setMessages(prev => [...prev, { type: "user", text: userQuery }]);
    
    // 2. Add placeholder chatbot message
    let chatbotMsg = { type: 'chatbot', text: '', sources: [], timing: null, error: null };
    setMessages(prev => [...prev, chatbotMsg]);

    const ac = new AbortController();
    streamAbortRef.current = ac;

    const apiUrl = joinUrl(API_BASE, "/api/chat/stream") + `?question=${encodeURIComponent(userQuery)}`;

    try {
      const response = await fetch(apiUrl, { 
        signal: ac.signal,
        headers: { 'ngrok-skip-browser-warning': 'true' }
      });
      if (!response.ok) throw new Error(`Server Error: ${response.status}`);
      if (!response.body) throw new Error("Readable stream not supported");

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.startsWith("data:")) continue;
          
          try {
            const data = JSON.parse(line.replace(/^data:\s*/, "").trim());
            
            if (data.type === "token") chatbotMsg.text += (data.text ?? "");
            else if (data.type === "sources") chatbotMsg.sources = data.items ?? [];
            else if (data.type === "perf_time") chatbotMsg.timing = data.data;
            else if (data.type === "error") chatbotMsg.error = data.message;
            else if (data.type === "done") break;

            setMessages(prev => {
              const next = [...prev];
              next[next.length - 1] = { ...chatbotMsg };
              return next;
            });
          } catch (e) {
            console.error("SSE Parse error", e);
          }
        }
      }
    } catch (error) {
      if (error?.name !== "AbortError") {
        const msg = error?.message || String(error);
        setStreamError(msg);
        setMessages(prev => {
          const next = [...prev];
          next[next.length - 1].error = msg;
          return next;
        });
      }
    } finally {
      setIsLoading(false);
      streamAbortRef.current = null;
    }
  };

  return (
    <div className="flex h-screen w-full flex-col bg-zinc-950 text-zinc-100 font-sans selection:bg-indigo-500/30 overflow-hidden">
      {/* Navbar */}
      <nav className="flex h-16 items-center justify-between border-b border-zinc-900 bg-zinc-950/50 px-6 backdrop-blur-md shrink-0">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-600 shadow-lg shadow-indigo-500/20 ring-1 ring-white/10">
            <Bot className="w-5 h-5 text-white" />
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-bold tracking-tight leading-none">RAG Chatbot <span className="text-indigo-500">Pro</span></span>
            <div className="mt-1 flex items-center gap-2">
              <div className={`h-1.5 w-1.5 rounded-full ${backend.status === 'up' ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]' : 'bg-red-500'}`} />
              <span className="text-[9px] font-bold uppercase tracking-widest text-zinc-500">
                {backend.status === 'up' ? backend.detail : 'Offline'}
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button 
            onClick={() => setView('chat')} 
            className={`flex items-center gap-2 rounded-lg px-4 py-2 text-xs font-bold uppercase tracking-wider transition-all border ${
              view === 'chat' ? 'bg-zinc-800 border-zinc-700 text-white' : 'border-transparent text-zinc-400 hover:text-zinc-200'
            }`}
          >
            <MessageSquare size={14} /> Chat
          </button>
          <button 
            onClick={() => setView('register')} 
            className={`flex items-center gap-2 rounded-lg px-4 py-2 text-xs font-bold uppercase tracking-wider transition-all border ${
              view === 'register' ? 'bg-zinc-800 border-zinc-700 text-white' : 'border-transparent text-zinc-400 hover:text-zinc-200'
            }`}
          >
            <UserPlus size={14} /> Register
          </button>
          <button 
            onClick={() => setView('debug')} 
            className={`flex items-center gap-2 rounded-lg px-4 py-2 text-xs font-bold uppercase tracking-wider transition-all border ${
              view === 'debug' ? 'bg-zinc-800 border-zinc-700 text-indigo-400' : 'border-transparent text-zinc-400 hover:text-zinc-200'
            }`}
          >
            <Terminal size={14} /> Debug
          </button>
        </div>
      </nav>

      {/* Main Content */}
      <main className="flex-1 relative overflow-hidden flex flex-col">
        {view === 'chat' && (
          <>
            <div className="flex-1 overflow-y-auto px-4 py-8">
              <div className="mx-auto max-w-3xl">
                {messages.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-20 text-center animate-in fade-in zoom-in duration-500">
                    <div className="mb-6 flex h-24 w-24 items-center justify-center rounded-full bg-zinc-900 ring-1 ring-zinc-800 shadow-inner">
                      <Bot className="w-12 h-12 text-zinc-800" />
                    </div>
                    <h2 className="text-2xl font-bold text-zinc-100">How can I help you today?</h2>
                    <p className="mt-2 max-w-md text-zinc-500 text-sm">
                      Ask anything about your documents or provide a prompt to start our session.
                    </p>
                  </div>
                ) : (
                  messages.map((m, i) => <ChatMessage key={i} {...m} />)
                )}
                <div ref={messagesEndRef} className="h-4" />
              </div>
            </div>

            <div className="bg-gradient-to-t from-zinc-950 via-zinc-950 to-transparent pt-10 pb-6 shrink-0">
              <div className="mx-auto max-w-3xl px-4">
                <form onSubmit={handleSendMessage} className="relative flex items-center rounded-2xl border border-zinc-800 bg-zinc-900/50 p-1.5 shadow-2xl focus-within:border-indigo-500/50 transition-all ring-1 ring-white/5">
                  <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    disabled={isLoading}
                    placeholder={isLoading ? "Generating response..." : "Ask a question about your docs..."}
                    className="flex-1 bg-transparent px-4 py-3 text-sm outline-none placeholder:text-zinc-600"
                  />
                  <div className="flex items-center gap-1">
                    {isLoading && (
                      <button type="button" onClick={handleStop} className="flex h-10 w-10 items-center justify-center rounded-xl text-zinc-400 hover:bg-zinc-800 transition-colors">
                        <StopCircle size={20} />
                      </button>
                    )}
                    <button 
                      type="submit" 
                      disabled={!input.trim() || isLoading} 
                      className={`flex h-10 w-10 items-center justify-center rounded-xl transition-all ${!input.trim() || isLoading ? 'bg-zinc-800 text-zinc-600' : 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/20 hover:bg-indigo-500'}`}
                    >
                      <Send size={18} />
                    </button>
                  </div>
                </form>
                
                {streamError && (
                  <div className="mt-3 flex items-center gap-2 rounded-xl bg-red-500/10 px-4 py-2 text-[11px] text-red-400 ring-1 ring-red-500/20">
                    <ShieldAlert size={12} />
                    <span className="font-bold uppercase tracking-wider">Stream Error:</span>
                    <span className="truncate">{streamError}</span>
                  </div>
                )}

                <div className="mt-4 flex items-center justify-between border-t border-zinc-900 pt-3">
                  <p className="text-[10px] font-medium text-zinc-600 uppercase tracking-widest">&copy; 2026 RAG-BOT INC</p>
                  <div className="flex gap-4">
                     <span className="text-[10px] font-medium text-zinc-600 uppercase tracking-widest flex items-center gap-1"><ShieldCheck size={10}/> SSL Encrypted</span>
                     <span className="text-[10px] font-medium text-zinc-600 uppercase tracking-widest flex items-center gap-1"><Globe size={10}/> Cloud Context</span>
                  </div>
                </div>
              </div>
            </div>
          </>
        )}

        {view === 'register' && (
          <div className="flex-1 flex items-center justify-center p-6 overflow-y-auto">
            <div className="w-full max-w-md space-y-8 rounded-3xl border border-zinc-900 bg-zinc-900/30 p-10 backdrop-blur-xl animate-in fade-in slide-in-from-top-4 duration-500 ring-1 ring-white/5 shadow-2xl">
              <div className="text-center">
                <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-indigo-600/10 text-indigo-500 ring-1 ring-indigo-500/20">
                  <UserPlus size={32} />
                </div>
                <h2 className="text-3xl font-bold tracking-tight">Create Account</h2>
                <p className="mt-2 text-sm text-zinc-500">Sign up to sync your document history across devices.</p>
              </div>
              <div className="space-y-5">
                {/* Identity Field */}
                <div className="space-y-1">
                  <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 ml-1">
                    EMAIL ADDRESS or PHONE NUMBER
                  </label>
                  <input 
                    className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-4 py-3 text-sm focus:border-indigo-500/50 outline-none transition-all placeholder:text-zinc-700" 
                    placeholder="name@example.com or phone number" 
                  />
                </div>

                {/* Password Field */}
                <div className="space-y-1">
                  <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 ml-1 flex justify-between items-center">
                    PASSWORD
                    <span className="text-[9px] text-indigo-400 normal-case italic">suggestion: use symbols & numbers</span>
                  </label>
                  <div className="relative">
                    <input 
                      type={showPassword ? "text" : "password"} 
                      className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-4 py-3 pr-12 text-sm focus:border-indigo-500/50 outline-none transition-all" 
                      placeholder="••••••••" 
                    />
                    <button 
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-600 hover:text-zinc-400 transition-colors"
                    >
                      {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  </div>
                  <p className="text-[10px] text-zinc-600 mt-1 ml-1 font-mono">
                    Suggestion: <span className="text-emerald-500/80">Tr0ub4dur&3!</span>
                  </p>
                </div>

                {/* Role Selection */}
                <div className="space-y-2 pt-2 border-t border-zinc-800/50">
                   <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 ml-1">Account Role</label>
                   <div className="flex gap-6 px-1">
                      <label className="flex items-center gap-2.5 group cursor-pointer">
                        <div className="relative flex h-5 w-5 items-center justify-center">
                          <input 
                            type="checkbox" 
                            className="peer h-full w-full cursor-pointer appearance-none rounded border border-zinc-700 bg-zinc-950 checked:bg-indigo-600 checked:border-indigo-500 transition-all"
                            checked={role === 'user'}
                            onChange={() => setRole('user')}
                          />
                          <Check size={14} className="pointer-events-none absolute text-white opacity-0 peer-checked:opacity-100 transition-opacity" />
                        </div>
                        <span className="text-sm font-medium text-zinc-400 group-hover:text-zinc-200 transition-colors">User</span>
                      </label>

                      <label className="flex items-center gap-2.5 group cursor-pointer">
                        <div className="relative flex h-5 w-5 items-center justify-center">
                          <input 
                            type="checkbox" 
                            className="peer h-full w-full cursor-pointer appearance-none rounded border border-zinc-700 bg-zinc-950 checked:bg-indigo-600 checked:border-indigo-500 transition-all"
                            checked={role === 'provider'}
                            onChange={() => setRole('provider')}
                          />
                          <Check size={14} className="pointer-events-none absolute text-white opacity-0 peer-checked:opacity-100 transition-opacity" />
                        </div>
                        <span className="text-sm font-medium text-zinc-400 group-hover:text-zinc-200 transition-colors">Provider</span>
                      </label>
                   </div>
                </div>
              </div>

              <button className="w-full rounded-xl bg-indigo-600 py-4 text-sm font-bold text-white shadow-lg shadow-indigo-500/20 hover:bg-indigo-500 transition-all">Sign Up Now</button>
              
              <p className="text-center text-[10px] text-zinc-600 uppercase tracking-widest">
                By signing up, you agree to our <span className="text-zinc-400 underline cursor-pointer">Terms of Service</span>
              </p>
            </div>
          </div>
        )}

        {view === 'debug' && (
          <div className="flex-1 p-8 overflow-y-auto">
            <div className="mx-auto max-w-3xl space-y-6">
              <div className="rounded-2xl border border-zinc-800 bg-zinc-900/30 p-6 backdrop-blur-sm">
                <h3 className="flex items-center gap-2 text-sm font-bold uppercase tracking-widest text-indigo-400 mb-4">
                  <Terminal size={16} /> Backend Diagnostics
                </h3>
                <div className="grid grid-cols-2 gap-4">
                   <div className="p-4 rounded-xl bg-zinc-950 border border-zinc-800">
                      <p className="text-[10px] text-zinc-500 uppercase mb-1">Health Status</p>
                      <p className={`text-sm font-mono ${backend.status === 'up' ? 'text-emerald-400' : 'text-red-400'}`}>{backend.status.toUpperCase()}</p>
                   </div>
                   <div className="p-4 rounded-xl bg-zinc-950 border border-zinc-800">
                      <p className="text-[10px] text-zinc-500 uppercase mb-1">API Endpoint</p>
                      <p className="text-sm font-mono text-zinc-300 truncate">{API_BASE}</p>
                   </div>
                </div>
                
                <div className="mt-6">
                  <p className="text-[10px] text-zinc-500 uppercase mb-2">System Capabilities</p>
                  <div className="flex flex-wrap gap-2">
                    <span className="rounded-md bg-zinc-900 px-2 py-1 text-[10px] font-bold text-zinc-400 border border-zinc-800">SSE STREAMING</span>
                    <span className="rounded-md bg-zinc-900 px-2 py-1 text-[10px] font-bold text-zinc-400 border border-zinc-800">BITNET 1.58B</span>
                    <span className="rounded-md bg-zinc-900 px-2 py-1 text-[10px] font-bold text-zinc-400 border border-zinc-800">CHROMA DB</span>
                  </div>
                </div>

                <button 
                  onClick={() => window.location.reload()}
                  className="mt-8 w-full py-3 rounded-xl bg-zinc-800 hover:bg-zinc-700 text-xs font-bold uppercase tracking-widest transition-all text-zinc-300"
                >
                  Force Refresh Connection
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}