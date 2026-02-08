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
  EyeOff,
  LogIn,
  Mail,
  ArrowLeft,
  RefreshCw,
  Loader2
} from 'lucide-react';

// --- Configuration ---
import API_BASE from "./api/apiBase";

// --- Helpers ---
function joinUrl(base, path) {
  const b = String(base || "").trim().replace(/\/+$/, "");
  const p = String(path || "").trim().replace(/^\/+/, "");
  return `${b}/${p}`;
}

const NGROK_HEADERS = {
  'Content-Type': 'application/json',
  'ngrok-skip-browser-warning': 'true'
};

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
  const [view, setView] = useState('chat'); // 'chat', 'register', 'login', 'verify', 'debug'
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [streamError, setStreamError] = useState(null);
  const [backend, setBackend] = useState({ status: "checking", detail: "" });
  const [currentUser, setCurrentUser] = useState(null);
  
  // Registration States
  const [showPassword, setShowPassword] = useState(false);
  const [role, setRole] = useState('user');
  const [regForm, setRegForm] = useState({ username: '', email: '', password: '', confirmPassword: '', age: '', phone: '' });
  const [regError, setRegError] = useState(null);
  const [regLoading, setRegLoading] = useState(false);
  const [suggestedPassword, setSuggestedPassword] = useState('');

  // Login States
  const [loginForm, setLoginForm] = useState({ email: '', password: '' });
  const [loginError, setLoginError] = useState(null);
  const [loginLoading, setLoginLoading] = useState(false);

  // Verification States
  const [verifyEmail, setVerifyEmail] = useState('');
  const [pinDigits, setPinDigits] = useState(['', '', '', '', '', '']);
  const [verifyError, setVerifyError] = useState(null);
  const [verifyLoading, setVerifyLoading] = useState(false);
  const [verifySuccess, setVerifySuccess] = useState(false);
  const [resendLoading, setResendLoading] = useState(false);
  const pinRefs = useRef([]);

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
        if (r.ok && j?.ok === true) {
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

  // --- REGISTRATION ---
  const handleRegister = async (e) => {
    e.preventDefault();
    setRegError(null);
    setRegLoading(true);

    try {
      const res = await fetch(joinUrl(API_BASE, "/api/auth/register"), {
        method: "POST",
        headers: NGROK_HEADERS,
        body: JSON.stringify({
          username: regForm.username,
          email: regForm.email,
          password: regForm.password,
          confirm_password: regForm.confirmPassword,
          age: parseInt(regForm.age),
          phone: regForm.phone || null
        })
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Registration failed");
      }

      // Move to verification view
      setVerifyEmail(regForm.email);
      setView('verify');
      setRegForm({ username: '', email: '', password: '', confirmPassword: '', age: '', phone: '' });
    } catch (err) {
      setRegError(err.message);
    } finally {
      setRegLoading(false);
    }
  };

  // --- LOGIN ---
  const handleLogin = async (e) => {
    e.preventDefault();
    setLoginError(null);
    setLoginLoading(true);

    try {
      const res = await fetch(joinUrl(API_BASE, "/api/auth/login"), {
        method: "POST",
        headers: NGROK_HEADERS,
        body: JSON.stringify({
          email: loginForm.email,
          password: loginForm.password
        })
      });

      const data = await res.json();

      if (!res.ok) {
        if (res.status === 403) {
          // Email not verified — go to verify view
          setVerifyEmail(loginForm.email);
          setView('verify');
          return;
        }
        throw new Error(data.detail || "Login failed");
      }

      setCurrentUser(data.user);
      setLoginForm({ email: '', password: '' });
      setView('chat');
    } catch (err) {
      setLoginError(err.message);
    } finally {
      setLoginLoading(false);
    }
  };

  // --- PIN VERIFICATION ---
  const handlePinChange = (index, value) => {
    if (value.length > 1) value = value.slice(-1);
    if (value && !/^\d$/.test(value)) return;

    const newDigits = [...pinDigits];
    newDigits[index] = value;
    setPinDigits(newDigits);

    // Auto-focus next input
    if (value && index < 5) {
      pinRefs.current[index + 1]?.focus();
    }
  };

  const handlePinKeyDown = (index, e) => {
    if (e.key === 'Backspace' && !pinDigits[index] && index > 0) {
      pinRefs.current[index - 1]?.focus();
    }
  };

  const handlePinPaste = (e) => {
    e.preventDefault();
    const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6);
    if (pasted.length === 6) {
      const newDigits = pasted.split('');
      setPinDigits(newDigits);
      pinRefs.current[5]?.focus();
    }
  };

  const handleVerifyPin = async () => {
    const pin = pinDigits.join('');
    if (pin.length !== 6) {
      setVerifyError("Please enter all 6 digits");
      return;
    }

    setVerifyError(null);
    setVerifyLoading(true);

    try {
      const res = await fetch(joinUrl(API_BASE, "/api/auth/verify-pin"), {
        method: "POST",
        headers: NGROK_HEADERS,
        body: JSON.stringify({ email: verifyEmail, pin })
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Verification failed");
      }

      setVerifySuccess(true);
      setTimeout(() => {
        setView('login');
        setVerifySuccess(false);
        setPinDigits(['', '', '', '', '', '']);
      }, 2000);
    } catch (err) {
      setVerifyError(err.message);
      setPinDigits(['', '', '', '', '', '']);
      pinRefs.current[0]?.focus();
    } finally {
      setVerifyLoading(false);
    }
  };

  const handleResendPin = async () => {
    setResendLoading(true);
    setVerifyError(null);

    try {
      const res = await fetch(joinUrl(API_BASE, "/api/auth/resend-pin"), {
        method: "POST",
        headers: NGROK_HEADERS,
        body: JSON.stringify({ email: verifyEmail })
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to resend");

      setVerifyError(null);
      setPinDigits(['', '', '', '', '', '']);
      pinRefs.current[0]?.focus();
    } catch (err) {
      setVerifyError(err.message);
    } finally {
      setResendLoading(false);
    }
  };

  const handleLogout = () => {
    setCurrentUser(null);
    setView('login');
  };

  // --- CHAT ---
  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userQuery = input.trim();
    setInput("");
    setIsLoading(true);
    setStreamError(null);

    setMessages(prev => [...prev, { type: "user", text: userQuery }]);
    
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

  // --- Password Generator ---
  const generateStrongPassword = () => {
    const upper = 'ABCDEFGHJKLMNPQRSTUVWXYZ';
    const lower = 'abcdefghjkmnpqrstuvwxyz';
    const numbers = '23456789';
    const symbols = '!@#$%&*?+=-';
    const all = upper + lower + numbers + symbols;
    
    let pass = '';
    pass += upper[Math.floor(Math.random() * upper.length)];
    pass += lower[Math.floor(Math.random() * lower.length)];
    pass += numbers[Math.floor(Math.random() * numbers.length)];
    pass += symbols[Math.floor(Math.random() * symbols.length)];
    
    for (let i = 4; i < 14; i++) {
      pass += all[Math.floor(Math.random() * all.length)];
    }
    
    // Shuffle
    pass = pass.split('').sort(() => Math.random() - 0.5).join('');
    setSuggestedPassword(pass);
  };

  const useSuggestedPassword = () => {
    setRegForm({ ...regForm, password: suggestedPassword, confirmPassword: suggestedPassword });
  };

  // --- Google Sign-In placeholder ---
  const handleGoogleSignIn = () => {
    alert("Google Sign-In will be available soon! Please use email registration for now.");
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

          {!currentUser ? (
            <>
              <button 
                onClick={() => setView('register')} 
                className={`flex items-center gap-2 rounded-lg px-4 py-2 text-xs font-bold uppercase tracking-wider transition-all border ${
                  view === 'register' ? 'bg-zinc-800 border-zinc-700 text-white' : 'border-transparent text-zinc-400 hover:text-zinc-200'
                }`}
              >
                <UserPlus size={14} /> Register
              </button>
              <button 
                onClick={() => setView('login')} 
                className={`flex items-center gap-2 rounded-lg px-4 py-2 text-xs font-bold uppercase tracking-wider transition-all border ${
                  view === 'login' ? 'bg-zinc-800 border-zinc-700 text-white' : 'border-transparent text-zinc-400 hover:text-zinc-200'
                }`}
              >
                <LogIn size={14} /> Sign In
              </button>
            </>
          ) : (
            <button 
              onClick={handleLogout} 
              className="flex items-center gap-2 rounded-lg px-4 py-2 text-xs font-bold uppercase tracking-wider transition-all border border-transparent text-zinc-400 hover:text-zinc-200"
            >
              <User size={14} /> {currentUser.username} (Sign Out)
            </button>
          )}

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

        {/* ==================== CHAT VIEW ==================== */}
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

        {/* ==================== REGISTER VIEW ==================== */}
        {view === 'register' && (
          <div className="flex-1 flex items-center justify-center p-6 overflow-y-auto">
            <div className="w-full max-w-md space-y-6 rounded-3xl border border-zinc-900 bg-zinc-900/30 p-10 backdrop-blur-xl animate-in fade-in slide-in-from-top-4 duration-500 ring-1 ring-white/5 shadow-2xl">
              <div className="text-center">
                <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-indigo-600/10 text-indigo-500 ring-1 ring-indigo-500/20">
                  <UserPlus size={32} />
                </div>
                <h2 className="text-3xl font-bold tracking-tight">Create Account</h2>
                <p className="mt-2 text-sm text-zinc-500">Sign up to get started with RAG Chatbot Pro.</p>
              </div>

              {/* Google Sign-In */}
              <button 
                onClick={handleGoogleSignIn}
                className="w-full flex items-center justify-center gap-3 rounded-xl border border-zinc-800 bg-zinc-950 py-3.5 text-sm font-medium text-zinc-300 hover:bg-zinc-900 hover:text-white transition-all"
              >
                <svg width="18" height="18" viewBox="0 0 24 24">
                  <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/>
                  <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                  <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                  <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
                </svg>
                Sign up with Google
              </button>

              <div className="flex items-center gap-3">
                <div className="flex-1 h-px bg-zinc-800"></div>
                <span className="text-[10px] font-bold uppercase tracking-widest text-zinc-600">or</span>
                <div className="flex-1 h-px bg-zinc-800"></div>
              </div>

              <form onSubmit={handleRegister} className="space-y-4">
                {/* Username */}
                <div className="space-y-1">
                  <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 ml-1">Username</label>
                  <input 
                    value={regForm.username}
                    onChange={(e) => setRegForm({...regForm, username: e.target.value})}
                    className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-4 py-3 text-sm focus:border-indigo-500/50 outline-none transition-all placeholder:text-zinc-700" 
                    placeholder="Choose a username"
                    required
                  />
                </div>

                {/* Email */}
                <div className="space-y-1">
                  <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 ml-1">Email Address</label>
                  <input 
                    type="email"
                    value={regForm.email}
                    onChange={(e) => setRegForm({...regForm, email: e.target.value})}
                    className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-4 py-3 text-sm focus:border-indigo-500/50 outline-none transition-all placeholder:text-zinc-700" 
                    placeholder="name@example.com"
                    required
                  />
                </div>

                {/* Password */}
                <div className="space-y-1">
                  <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 ml-1 flex justify-between items-center">
                    Password
                    <span className="text-[9px] text-indigo-400 normal-case italic">use symbols & numbers</span>
                  </label>
                  <div className="relative">
                    <input 
                      type={showPassword ? "text" : "password"} 
                      value={regForm.password}
                      onChange={(e) => setRegForm({...regForm, password: e.target.value})}
                      className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-4 py-3 pr-12 text-sm focus:border-indigo-500/50 outline-none transition-all" 
                      placeholder="Min. 8 characters"
                      required
                    />
                    <button 
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-600 hover:text-zinc-400 transition-colors"
                    >
                      {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  </div>
                  <div className="flex items-center gap-2 mt-1.5 ml-1">
                    <button 
                      type="button"
                      onClick={generateStrongPassword}
                      className="text-[10px] text-indigo-400 hover:text-indigo-300 font-medium transition-colors"
                    >
                      Generate strong password
                    </button>
                    {suggestedPassword && (
                      <div className="flex items-center gap-2">
                        <code className="text-[10px] text-emerald-500/80 font-mono bg-zinc-900 px-2 py-0.5 rounded">{suggestedPassword}</code>
                        <button 
                          type="button"
                          onClick={useSuggestedPassword}
                          className="text-[10px] text-indigo-400 hover:text-indigo-300 font-bold uppercase transition-colors"
                        >
                          Use
                        </button>
                      </div>
                    )}
                  </div>
                </div>

                {/* Confirm Password */}
                <div className="space-y-1">
                  <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 ml-1">Confirm Password</label>
                  <input 
                    type="password"
                    value={regForm.confirmPassword}
                    onChange={(e) => setRegForm({...regForm, confirmPassword: e.target.value})}
                    className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-4 py-3 text-sm focus:border-indigo-500/50 outline-none transition-all" 
                    placeholder="Repeat your password"
                    required
                  />
                </div>

                {/* Age */}
                <div className="space-y-1">
                  <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 ml-1">Age</label>
                  <input 
                    type="number"
                    value={regForm.age}
                    onChange={(e) => setRegForm({...regForm, age: e.target.value})}
                    className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-4 py-3 text-sm focus:border-indigo-500/50 outline-none transition-all placeholder:text-zinc-700" 
                    placeholder="Must be 13 or older"
                    min="13"
                    max="120"
                    required
                  />
                </div>

                {/* Phone (optional) */}
                <div className="space-y-1">
                  <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 ml-1">
                    Phone Number <span className="text-zinc-700">(optional)</span>
                  </label>
                  <input 
                    type="tel"
                    value={regForm.phone}
                    onChange={(e) => setRegForm({...regForm, phone: e.target.value})}
                    className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-4 py-3 text-sm focus:border-indigo-500/50 outline-none transition-all placeholder:text-zinc-700" 
                    placeholder="+1234567890"
                  />
                </div>

                {/* Account Role */}
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

                {regError && (
                  <div className="flex items-center gap-2 rounded-xl bg-red-500/10 px-4 py-2.5 text-xs text-red-400 ring-1 ring-red-500/20">
                    <ShieldAlert size={14} />
                    <span>{regError}</span>
                  </div>
                )}

                <button 
                  type="submit"
                  disabled={regLoading}
                  className="w-full rounded-xl bg-indigo-600 py-4 text-sm font-bold text-white shadow-lg shadow-indigo-500/20 hover:bg-indigo-500 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {regLoading ? <><Loader2 size={16} className="animate-spin" /> Creating Account...</> : 'Sign Up Now'}
                </button>
              </form>

              <p className="text-center text-sm text-zinc-500">
                Already have an account?{' '}
                <button onClick={() => setView('login')} className="text-indigo-400 hover:text-indigo-300 font-medium transition-colors">
                  Sign In
                </button>
              </p>

              <p className="text-center text-[10px] text-zinc-600 uppercase tracking-widest">
                By signing up, you agree to our <span className="text-zinc-400 underline cursor-pointer hover:text-zinc-200 transition-colors">Terms of Service</span>
              </p>
            </div>
          </div>
        )}

        {/* ==================== LOGIN VIEW ==================== */}
        {view === 'login' && (
          <div className="flex-1 flex items-center justify-center p-6 overflow-y-auto">
            <div className="w-full max-w-md space-y-6 rounded-3xl border border-zinc-900 bg-zinc-900/30 p-10 backdrop-blur-xl animate-in fade-in slide-in-from-top-4 duration-500 ring-1 ring-white/5 shadow-2xl">
              <div className="text-center">
                <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-indigo-600/10 text-indigo-500 ring-1 ring-indigo-500/20">
                  <LogIn size={32} />
                </div>
                <h2 className="text-3xl font-bold tracking-tight">Welcome Back</h2>
                <p className="mt-2 text-sm text-zinc-500">Sign in to your account to continue.</p>
              </div>

              {/* Google Sign-In */}
              <button 
                onClick={handleGoogleSignIn}
                className="w-full flex items-center justify-center gap-3 rounded-xl border border-zinc-800 bg-zinc-950 py-3.5 text-sm font-medium text-zinc-300 hover:bg-zinc-900 hover:text-white transition-all"
              >
                <svg width="18" height="18" viewBox="0 0 24 24">
                  <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/>
                  <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                  <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                  <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
                </svg>
                Sign in with Google
              </button>

              <div className="flex items-center gap-3">
                <div className="flex-1 h-px bg-zinc-800"></div>
                <span className="text-[10px] font-bold uppercase tracking-widest text-zinc-600">or</span>
                <div className="flex-1 h-px bg-zinc-800"></div>
              </div>

              <form onSubmit={handleLogin} className="space-y-4">
                <div className="space-y-1">
                  <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 ml-1">Email Address</label>
                  <input 
                    type="email"
                    value={loginForm.email}
                    onChange={(e) => setLoginForm({...loginForm, email: e.target.value})}
                    className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-4 py-3 text-sm focus:border-indigo-500/50 outline-none transition-all placeholder:text-zinc-700" 
                    placeholder="name@example.com"
                    required
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 ml-1">Password</label>
                  <div className="relative">
                    <input 
                      type={showPassword ? "text" : "password"} 
                      value={loginForm.password}
                      onChange={(e) => setLoginForm({...loginForm, password: e.target.value})}
                      className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-4 py-3 pr-12 text-sm focus:border-indigo-500/50 outline-none transition-all" 
                      placeholder="Enter your password"
                      required
                    />
                    <button 
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-600 hover:text-zinc-400 transition-colors"
                    >
                      {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  </div>
                </div>

                {loginError && (
                  <div className="flex items-center gap-2 rounded-xl bg-red-500/10 px-4 py-2.5 text-xs text-red-400 ring-1 ring-red-500/20">
                    <ShieldAlert size={14} />
                    <span>{loginError}</span>
                  </div>
                )}

                <button 
                  type="submit"
                  disabled={loginLoading}
                  className="w-full rounded-xl bg-indigo-600 py-4 text-sm font-bold text-white shadow-lg shadow-indigo-500/20 hover:bg-indigo-500 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {loginLoading ? <><Loader2 size={16} className="animate-spin" /> Signing In...</> : 'Sign In'}
                </button>
              </form>

              <p className="text-center text-sm text-zinc-500">
                Don't have an account?{' '}
                <button onClick={() => setView('register')} className="text-indigo-400 hover:text-indigo-300 font-medium transition-colors">
                  Sign Up
                </button>
              </p>
            </div>
          </div>
        )}

        {/* ==================== VERIFY PIN VIEW ==================== */}
        {view === 'verify' && (
          <div className="flex-1 flex items-center justify-center p-6 overflow-y-auto">
            <div className="w-full max-w-md space-y-6 rounded-3xl border border-zinc-900 bg-zinc-900/30 p-10 backdrop-blur-xl animate-in fade-in slide-in-from-top-4 duration-500 ring-1 ring-white/5 shadow-2xl">
              <button 
                onClick={() => setView('register')}
                className="flex items-center gap-1.5 text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
              >
                <ArrowLeft size={14} /> Back
              </button>

              <div className="text-center">
                <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-indigo-600/10 text-indigo-500 ring-1 ring-indigo-500/20">
                  <Mail size={32} />
                </div>
                <h2 className="text-3xl font-bold tracking-tight">Check Your Email</h2>
                <p className="mt-2 text-sm text-zinc-500">
                  We sent a 6-digit code to <span className="text-indigo-400 font-medium">{verifyEmail}</span>
                </p>
              </div>

              {verifySuccess ? (
                <div className="flex flex-col items-center gap-3 py-8">
                  <div className="flex h-16 w-16 items-center justify-center rounded-full bg-emerald-500/10 ring-1 ring-emerald-500/20">
                    <Check size={32} className="text-emerald-400" />
                  </div>
                  <p className="text-lg font-bold text-emerald-400">Email Verified!</p>
                  <p className="text-sm text-zinc-500">Redirecting to sign in...</p>
                </div>
              ) : (
                <>
                  {/* PIN Input */}
                  <div className="flex justify-center gap-3">
                    {pinDigits.map((digit, i) => (
                      <input
                        key={i}
                        ref={(el) => (pinRefs.current[i] = el)}
                        type="text"
                        inputMode="numeric"
                        maxLength={1}
                        value={digit}
                        onChange={(e) => handlePinChange(i, e.target.value)}
                        onKeyDown={(e) => handlePinKeyDown(i, e)}
                        onPaste={i === 0 ? handlePinPaste : undefined}
                        className={`h-14 w-12 rounded-xl border text-center text-xl font-bold outline-none transition-all ${
                          digit 
                            ? 'border-indigo-500 bg-indigo-500/10 text-indigo-400' 
                            : 'border-zinc-800 bg-zinc-950 text-zinc-100'
                        } focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20`}
                      />
                    ))}
                  </div>

                  {verifyError && (
                    <div className="flex items-center gap-2 rounded-xl bg-red-500/10 px-4 py-2.5 text-xs text-red-400 ring-1 ring-red-500/20">
                      <ShieldAlert size={14} />
                      <span>{verifyError}</span>
                    </div>
                  )}

                  <button 
                    onClick={handleVerifyPin}
                    disabled={verifyLoading || pinDigits.join('').length !== 6}
                    className="w-full rounded-xl bg-indigo-600 py-4 text-sm font-bold text-white shadow-lg shadow-indigo-500/20 hover:bg-indigo-500 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                  >
                    {verifyLoading ? <><Loader2 size={16} className="animate-spin" /> Verifying...</> : 'Verify Email'}
                  </button>

                  <div className="text-center">
                    <p className="text-sm text-zinc-500">
                      Didn't receive a code?{' '}
                      <button 
                        onClick={handleResendPin}
                        disabled={resendLoading}
                        className="text-indigo-400 hover:text-indigo-300 font-medium transition-colors disabled:opacity-50 inline-flex items-center gap-1"
                      >
                        {resendLoading ? <><Loader2 size={12} className="animate-spin" /> Sending...</> : <><RefreshCw size={12} /> Resend Code</>}
                      </button>
                    </p>
                  </div>
                </>
              )}
            </div>
          </div>
        )}

        {/* ==================== DEBUG VIEW ==================== */}
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
                   <div className="p-4 rounded-xl bg-zinc-950 border border-zinc-800">
                      <p className="text-[10px] text-zinc-500 uppercase mb-1">Logged In As</p>
                      <p className="text-sm font-mono text-zinc-300">{currentUser ? currentUser.username : 'Not signed in'}</p>
                   </div>
                   <div className="p-4 rounded-xl bg-zinc-950 border border-zinc-800">
                      <p className="text-[10px] text-zinc-500 uppercase mb-1">Auth Status</p>
                      <p className={`text-sm font-mono ${currentUser ? 'text-emerald-400' : 'text-amber-400'}`}>{currentUser ? 'AUTHENTICATED' : 'GUEST'}</p>
                   </div>
                </div>
                
                <div className="mt-6">
                  <p className="text-[10px] text-zinc-500 uppercase mb-2">System Capabilities</p>
                  <div className="flex flex-wrap gap-2">
                    <span className="rounded-md bg-zinc-900 px-2 py-1 text-[10px] font-bold text-zinc-400 border border-zinc-800">SSE STREAMING</span>
                    <span className="rounded-md bg-zinc-900 px-2 py-1 text-[10px] font-bold text-zinc-400 border border-zinc-800">BITNET 1.58B</span>
                    <span className="rounded-md bg-zinc-900 px-2 py-1 text-[10px] font-bold text-zinc-400 border border-zinc-800">CHROMA DB</span>
                    <span className="rounded-md bg-zinc-900 px-2 py-1 text-[10px] font-bold text-zinc-400 border border-zinc-800">GMAIL SMTP</span>
                    <span className="rounded-md bg-zinc-900 px-2 py-1 text-[10px] font-bold text-zinc-400 border border-zinc-800">JWT AUTH</span>
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