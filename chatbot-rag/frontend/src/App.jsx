import React, { useState, useEffect, useRef } from 'react';
import { 
  Check, X, Clock, Bot, User, Send, StopCircle, MessageSquare,
  ShieldCheck, Globe, Terminal, UserPlus, ShieldAlert, Eye, EyeOff,
  LogIn, Mail, ArrowLeft, RefreshCw, Loader2, Menu, UserCircle,
  ClipboardList, Plus, Calendar, Trash2, CheckCircle2, Circle, Camera, Save,
  ChevronLeft, ChevronRight, Archive
} from 'lucide-react';

import API_BASE from "./api/apiBase";

// --- Helpers ---
function joinUrl(base, path) {
  const b = String(base || "").trim().replace(/\/+$/, "");
  const p = String(path || "").trim().replace(/^\/+/, "");
  return `${b}/${p}`;
}

function authHeaders(token) {
  return {
    'Content-Type': 'application/json',
    'ngrok-skip-browser-warning': 'true',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {})
  };
}

function capitalize(str) {
  if (!str) return '';
  return str.charAt(0).toUpperCase() + str.slice(1);
}

const NGROK_HEADERS = {
  'Content-Type': 'application/json',
  'ngrok-skip-browser-warning': 'true'
};

// --- Chat Message Component ---
const ChatMessage = ({ type, text, sources = [], timing, error, profilePic, created_at }) => {
  const isUser = type === 'user';
  const timeStr = created_at ? (() => {
    try {
      const d = new Date(created_at);
      return d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
    } catch { return ''; }
  })() : '';
  return (
    <div className={`group flex w-full flex-col ${isUser ? 'items-end' : 'items-start'} mb-8`}>
      <div className={`flex max-w-[85%] gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
        {isUser && profilePic ? (
          <img src={profilePic} alt="" className="h-9 w-9 shrink-0 rounded-full object-cover border border-indigo-500 shadow-sm" />
        ) : (
          <div className={`flex h-9 w-9 shrink-0 select-none items-center justify-center rounded-full border shadow-sm ${
            isUser ? 'bg-indigo-600 border-indigo-500 text-white' : 'bg-zinc-800 border-zinc-700 text-zinc-300'
          }`}>
            {isUser ? <User size={18} /> : <Bot size={18} />}
          </div>
        )}
        <div className={`relative flex flex-col gap-2 rounded-2xl px-4 py-3 text-sm shadow-sm ring-1 ${
          isUser ? 'bg-indigo-600 text-white ring-indigo-500' : 'bg-zinc-900/50 text-zinc-100 ring-zinc-800 backdrop-blur-sm'
        }`}>
          {error ? (
            <div className="flex items-center gap-2 text-red-300 font-medium">
              <ShieldAlert size={14} /> <span>{error}</span>
            </div>
          ) : (
            <div className="whitespace-pre-wrap leading-relaxed">{text || (isUser ? "" : "...")}</div>
          )}
          <div className={`mt-1 flex items-center gap-3 text-[10px] uppercase tracking-wider font-bold border-t border-white/5 pt-2 ${isUser ? 'text-indigo-200' : 'text-zinc-500'}`}>
            {timeStr && <span>{timeStr}</span>}
            {timing && (
              <span className="flex items-center gap-1">
                <Clock size={10} className={isUser ? "text-indigo-200" : "text-amber-400"} /> {timing}s
              </span>
            )}
          </div>
        </div>
      </div>
      {!isUser && sources.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2 pl-12">
          {sources.map((s, i) => (
            <div key={i} title={s.preview} className="flex items-center gap-1.5 rounded-lg border border-zinc-800 bg-zinc-900/30 px-2.5 py-1 text-[11px] text-zinc-400 hover:bg-zinc-800 cursor-help">
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
  const [view, setView] = useState('chat');
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [streamError, setStreamError] = useState(null);
  const [currentQuarter, setCurrentQuarter] = useState(null);
  const [viewingQuarter, setViewingQuarter] = useState(null);
  const [availableQuarters, setAvailableQuarters] = useState([]);
  const [backend, setBackend] = useState({ status: "checking", detail: "" });
  const [currentUser, setCurrentUser] = useState(null);
  const [authToken, setAuthToken] = useState(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Registration
  const [showPassword, setShowPassword] = useState(false);
  const [role, setRole] = useState('user');
  const [regForm, setRegForm] = useState({ username: '', email: '', password: '', confirmPassword: '', age: '', phone: '' });
  const [regError, setRegError] = useState(null);
  const [regLoading, setRegLoading] = useState(false);
  const [suggestedPassword, setSuggestedPassword] = useState('');

  // Login
  const [loginForm, setLoginForm] = useState({ email: '', password: '' });
  const [loginError, setLoginError] = useState(null);
  const [loginLoading, setLoginLoading] = useState(false);

  // Verification
  const [verifyEmail, setVerifyEmail] = useState('');
  const [pinDigits, setPinDigits] = useState(['', '', '', '', '', '']);
  const [verifyError, setVerifyError] = useState(null);
  const [verifyLoading, setVerifyLoading] = useState(false);
  const [verifySuccess, setVerifySuccess] = useState(false);
  const [resendLoading, setResendLoading] = useState(false);
  const pinRefs = useRef([]);

  // Profile & Tasks
  const [tasks, setTasks] = useState([]);
  const [tasksLoading, setTasksLoading] = useState(false);
  const [usersList, setUsersList] = useState([]);
  const [newTask, setNewTask] = useState({ title: '', description: '', assigned_to: '', due_date: '' });
  const [taskError, setTaskError] = useState(null);
  const [profilePic, setProfilePic] = useState(null);
  const profilePicRef = useRef(null);
  const [profileData, setProfileData] = useState({
    fullName: '', preferredName: '', pronouns: '', dob: '', contactPhone: '', contactEmail: '',
    emergencyName: '', emergencyRelation: '', emergencyPhone: '',
    parent1FullName: '', parent1PreferredName: '', parent1Pronouns: '', parent1Dob: '',
    parent1ContactPhone: '', parent1ContactEmail: '',
    parent1EmergencyName: '', parent1EmergencyRelation: '', parent1EmergencyPhone: '',
    parent2FullName: '', parent2PreferredName: '', parent2Pronouns: '', parent2Dob: '',
    parent2ContactPhone: '', parent2ContactEmail: '',
    parent2EmergencyName: '', parent2EmergencyRelation: '', parent2EmergencyPhone: '',
    consentAcknowledged: false, confidentialityExplained: false,
    sessionFormat: '', paymentInfo: ''
  });
  const [profileSaved, setProfileSaved] = useState(false);

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
        const r = await fetch(url, { signal: ac.signal, headers: { 'ngrok-skip-browser-warning': 'true' } });
        const j = await r.json().catch(() => null);
        if (!alive) return;
        if (r.ok && j?.ok === true) setBackend({ status: "up", detail: "Model Ready" });
        else setBackend({ status: "down", detail: `HTTP ${r.status}` });
      } catch (e) {
        if (alive) setBackend({ status: "down", detail: "Offline" });
      }
    };
    checkStatus();
    const t = setInterval(checkStatus, 10000);
    return () => { alive = false; clearInterval(t); ac.abort(); };
  }, []);

  // Load chat history when user logs in
  useEffect(() => {
    if (authToken && currentUser) {
      loadChatHistory();
    }
  }, [authToken]);

  const loadChatHistory = async (year = null, quarter = null) => {
    try {
      let url = joinUrl(API_BASE, "/api/chat/history");
      const params = [];
      if (year) params.push(`year=${year}`);
      if (quarter) params.push(`quarter=${quarter}`);
      if (params.length) url += `?${params.join('&')}`;

      const res = await fetch(url, { headers: authHeaders(authToken) });
      if (res.ok) {
        const data = await res.json();
        if (data.current_quarter) setCurrentQuarter(data.current_quarter);
        if (data.viewing) setViewingQuarter(data.viewing);
        if (data.messages && data.messages.length > 0) {
          setMessages(data.messages.map(m => ({
            type: m.type,
            text: m.text,
            sources: m.sources || [],
            timing: m.timing,
            created_at: m.created_at
          })));
        } else {
          setMessages([]);
        }
      }
      // Also load available quarters
      const qRes = await fetch(joinUrl(API_BASE, "/api/chat/quarters"), { headers: authHeaders(authToken) });
      if (qRes.ok) {
        const qData = await qRes.json();
        setAvailableQuarters(qData.quarters || []);
      }
    } catch (e) {
      console.error("Failed to load chat history:", e);
    }
  };

  const saveChatMessage = async (role, text, sources = null, timing = null) => {
    if (!authToken) return;
    try {
      await fetch(joinUrl(API_BASE, "/api/chat/history"), {
        method: "POST",
        headers: authHeaders(authToken),
        body: JSON.stringify({ role, text, sources: sources ? JSON.stringify(sources) : null, timing })
      });
    } catch (e) {
      console.error("Failed to save message:", e);
    }
  };

  const handleClearHistory = async () => {
    if (!authToken) return;
    if (!confirm("This will clear the current chat view. Your history is preserved in archives.")) return;
    try {
      await fetch(joinUrl(API_BASE, "/api/chat/history"), {
        method: "DELETE",
        headers: authHeaders(authToken)
      });
      setMessages([]);
    } catch (e) {
      console.error("Failed to clear history:", e);
    }
  };

  const navigateQuarter = (direction) => {
    if (!viewingQuarter) return;
    let { year, quarter } = viewingQuarter;
    if (direction === 'prev') {
      quarter -= 1;
      if (quarter < 1) { quarter = 4; year -= 1; }
    } else {
      quarter += 1;
      if (quarter > 4) { quarter = 1; year += 1; }
    }
    setViewingQuarter({ year, quarter });
    loadChatHistory(year, quarter);
  };

  const goToCurrentQuarter = () => {
    if (currentQuarter) {
      setViewingQuarter(currentQuarter);
      loadChatHistory(currentQuarter.year, currentQuarter.quarter);
    }
  };

  const quarterLabel = (q) => {
    if (!q) return '';
    const names = { 1: 'Jan–Mar', 2: 'Apr–Jun', 3: 'Jul–Sep', 4: 'Oct–Dec' };
    return `Q${q.quarter} ${q.year} (${names[q.quarter]})`;
  };

  // Group messages by date
  const groupMessagesByDate = (msgs) => {
    const groups = [];
    let lastDate = null;
    for (const msg of msgs) {
      const dateStr = msg.created_at?.substring(0, 10) || '';
      if (dateStr && dateStr !== lastDate) {
        lastDate = dateStr;
        groups.push({ type: 'date-header', date: dateStr });
      }
      groups.push(msg);
    }
    return groups;
  };

  const formatDateHeader = (dateStr) => {
    try {
      const d = new Date(dateStr + 'T00:00:00');
      const today = new Date(); today.setHours(0,0,0,0);
      const yesterday = new Date(today); yesterday.setDate(yesterday.getDate() - 1);
      if (d.getTime() === today.getTime()) return 'Today';
      if (d.getTime() === yesterday.getTime()) return 'Yesterday';
      return d.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' });
    } catch { return dateStr; }
  };

  // Profile picture & data
  useEffect(() => {
    if (currentUser) {
      const savedPic = window.localStorage?.getItem(`profilePic_${currentUser.id}`);
      if (savedPic) setProfilePic(savedPic);
      else setProfilePic(null);

      const savedData = window.localStorage?.getItem(`profileData_${currentUser.id}`);
      if (savedData) {
        try { setProfileData(prev => ({ ...prev, ...JSON.parse(savedData) })); } catch {}
      }
    }
  }, [currentUser]);

  const handleProfilePicChange = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 2 * 1024 * 1024) { alert("Image must be under 2MB"); return; }
    const reader = new FileReader();
    reader.onload = (ev) => {
      const dataUrl = ev.target.result;
      setProfilePic(dataUrl);
      try { window.localStorage?.setItem(`profilePic_${currentUser.id}`, dataUrl); } catch {}
    };
    reader.readAsDataURL(file);
  };

  const removeProfilePic = () => {
    setProfilePic(null);
    try { window.localStorage?.removeItem(`profilePic_${currentUser.id}`); } catch {}
  };

  const saveProfileData = () => {
    try {
      window.localStorage?.setItem(`profileData_${currentUser.id}`, JSON.stringify(profileData));
      setProfileSaved(true);
      setTimeout(() => setProfileSaved(false), 2000);
    } catch {}
  };

  const updateProfile = (field, value) => {
    setProfileData(prev => ({ ...prev, [field]: value }));
    setProfileSaved(false);
  };

  // Load tasks
  const loadTasks = async () => {
    if (!authToken) return;
    setTasksLoading(true);
    try {
      const res = await fetch(joinUrl(API_BASE, "/api/tasks"), {
        headers: authHeaders(authToken)
      });
      if (res.ok) {
        const data = await res.json();
        setTasks(data.tasks || []);
      }
    } catch (e) {
      console.error("Failed to load tasks:", e);
    } finally {
      setTasksLoading(false);
    }
  };

  const loadUsers = async () => {
    if (!authToken || currentUser?.role !== 'provider') return;
    try {
      const res = await fetch(joinUrl(API_BASE, "/api/users"), {
        headers: authHeaders(authToken)
      });
      if (res.ok) {
        const data = await res.json();
        setUsersList(data.users || []);
      }
    } catch (e) {
      console.error("Failed to load users:", e);
    }
  };

  useEffect(() => {
    if (view === 'profile' && authToken) {
      loadTasks();
      if (currentUser?.role === 'provider') loadUsers();
    }
  }, [view, authToken]);

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
          role: role,
          phone: regForm.phone || null
        })
      });

      const data = await res.json();
      if (!res.ok) {
        let errorMsg = "Registration failed";
        if (typeof data.detail === 'string') errorMsg = data.detail;
        else if (Array.isArray(data.detail)) errorMsg = data.detail.map(e => e.msg || e.message || JSON.stringify(e)).join(', ');
        throw new Error(errorMsg);
      }

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
        body: JSON.stringify({ email: loginForm.email, password: loginForm.password })
      });

      const data = await res.json();
      if (!res.ok) {
        if (res.status === 403) {
          setVerifyEmail(loginForm.email);
          setView('verify');
          return;
        }
        throw new Error(typeof data.detail === 'string' ? data.detail : Array.isArray(data.detail) ? data.detail.map(e => e.msg || e.message || JSON.stringify(e)).join(', ') : "Login failed");
      }

      setAuthToken(data.access_token);
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
    if (value && index < 5) pinRefs.current[index + 1]?.focus();
  };

  const handlePinKeyDown = (index, e) => {
    if (e.key === 'Backspace' && !pinDigits[index] && index > 0) pinRefs.current[index - 1]?.focus();
  };

  const handlePinPaste = (e) => {
    e.preventDefault();
    const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6);
    if (pasted.length === 6) {
      setPinDigits(pasted.split(''));
      pinRefs.current[5]?.focus();
    }
  };

  const handleVerifyPin = async () => {
    const pin = pinDigits.join('');
    if (pin.length !== 6) { setVerifyError("Please enter all 6 digits"); return; }
    setVerifyError(null);
    setVerifyLoading(true);
    try {
      const res = await fetch(joinUrl(API_BASE, "/api/auth/verify-pin"), {
        method: "POST", headers: NGROK_HEADERS,
        body: JSON.stringify({ email: verifyEmail, pin })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Verification failed");
      setVerifySuccess(true);
      setTimeout(() => { setView('login'); setVerifySuccess(false); setPinDigits(['', '', '', '', '', '']); }, 2000);
    } catch (err) {
      setVerifyError(err.message);
      setPinDigits(['', '', '', '', '', '']);
      pinRefs.current[0]?.focus();
    } finally { setVerifyLoading(false); }
  };

  const handleResendPin = async () => {
    setResendLoading(true); setVerifyError(null);
    try {
      const res = await fetch(joinUrl(API_BASE, "/api/auth/resend-pin"), {
        method: "POST", headers: NGROK_HEADERS,
        body: JSON.stringify({ email: verifyEmail })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to resend");
      setPinDigits(['', '', '', '', '', '']);
      pinRefs.current[0]?.focus();
    } catch (err) { setVerifyError(err.message); }
    finally { setResendLoading(false); }
  };

  const handleLogout = () => {
    setCurrentUser(null);
    setAuthToken(null);
    setMessages([]);
    setTasks([]);
    setView('login');
  };

  // --- PASSWORD GENERATOR ---
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
    for (let i = 4; i < 14; i++) pass += all[Math.floor(Math.random() * all.length)];
    pass = pass.split('').sort(() => Math.random() - 0.5).join('');
    setSuggestedPassword(pass);
  };

  const useSuggestedPassword = () => {
    setRegForm({ ...regForm, password: suggestedPassword, confirmPassword: suggestedPassword });
  };

  // --- Google Sign-In ---
  const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || "";

  useEffect(() => {
    if (!GOOGLE_CLIENT_ID) return;
    const script = document.createElement('script');
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.defer = true;
    script.onload = () => {
      window.google?.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: handleGoogleResponse,
      });
    };
    document.head.appendChild(script);
    return () => { document.head.removeChild(script); };
  }, []);

  const handleGoogleResponse = async (response) => {
    try {
      const res = await fetch(joinUrl(API_BASE, "/api/auth/google"), {
        method: "POST", headers: NGROK_HEADERS,
        body: JSON.stringify({ token: response.credential })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : "Google sign-in failed");
      setAuthToken(data.access_token);
      setCurrentUser(data.user);
      setView('chat');
    } catch (err) {
      if (view === 'register') setRegError(err.message);
      else if (view === 'login') setLoginError(err.message);
      else alert(err.message);
    }
  };

  const handleGoogleSignIn = () => {
    if (!GOOGLE_CLIENT_ID || !window.google) { alert("Google Sign-In is not configured yet."); return; }
    window.google.accounts.id.prompt((notification) => {
      if (notification.isNotDisplayed() || notification.isSkippedMoment()) {
        const btn = document.getElementById('google-signin-fallback');
        if (btn) {
          btn.innerHTML = '';
          window.google.accounts.id.renderButton(btn, { theme: 'filled_black', size: 'large', width: '100%', text: view === 'register' ? 'signup_with' : 'signin_with' });
        }
      }
    });
  };

  // --- TASK MANAGEMENT ---
  const handleCreateTask = async (e) => {
    e.preventDefault();
    setTaskError(null);
    try {
      const res = await fetch(joinUrl(API_BASE, "/api/tasks"), {
        method: "POST",
        headers: authHeaders(authToken),
        body: JSON.stringify({
          title: newTask.title,
          description: newTask.description,
          assigned_to: parseInt(newTask.assigned_to),
          due_date: newTask.due_date || null
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to create task");
      setNewTask({ title: '', description: '', assigned_to: '', due_date: '' });
      loadTasks();
    } catch (err) {
      setTaskError(err.message);
    }
  };

  const handleToggleTask = async (taskId, currentStatus) => {
    const newStatus = currentStatus === 'completed' ? 'pending' : 'completed';
    try {
      await fetch(joinUrl(API_BASE, `/api/tasks/${taskId}`), {
        method: "PUT",
        headers: authHeaders(authToken),
        body: JSON.stringify({ status: newStatus })
      });
      loadTasks();
    } catch (e) {
      console.error("Failed to update task:", e);
    }
  };

  // --- CHAT ---
  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userQuery = input.trim();
    setInput("");
    setIsLoading(true);
    setStreamError(null);

    setMessages(prev => [...prev, { type: "user", text: userQuery, created_at: new Date().toISOString() }]);
    saveChatMessage("user", userQuery);

    let chatbotMsg = { type: 'chatbot', text: '', sources: [], timing: null, error: null, created_at: new Date().toISOString() };
    setMessages(prev => [...prev, chatbotMsg]);

    const ac = new AbortController();
    streamAbortRef.current = ac;
    const apiUrl = joinUrl(API_BASE, "/api/chat/stream") + `?question=${encodeURIComponent(userQuery)}`;

    try {
      const response = await fetch(apiUrl, { signal: ac.signal, headers: { 'ngrok-skip-browser-warning': 'true' } });
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
            setMessages(prev => { const next = [...prev]; next[next.length - 1] = { ...chatbotMsg }; return next; });
          } catch (e) { console.error("SSE Parse error", e); }
        }
      }

      // Save bot response to history
      if (chatbotMsg.text) {
        saveChatMessage("chatbot", chatbotMsg.text, chatbotMsg.sources, chatbotMsg.timing);
      }
    } catch (error) {
      if (error?.name !== "AbortError") {
        const msg = error?.message || String(error);
        setStreamError(msg);
        setMessages(prev => { const next = [...prev]; next[next.length - 1].error = msg; return next; });
      }
    } finally {
      setIsLoading(false);
      streamAbortRef.current = null;
    }
  };

  // --- NAV HELPER ---
  const navTo = (v) => { setView(v); setMobileMenuOpen(false); };

  return (
    <div className="flex h-screen w-full flex-col bg-zinc-950 text-zinc-100 font-sans selection:bg-indigo-500/30 overflow-hidden">
      {/* Navbar */}
      <nav className="relative border-b border-zinc-900 bg-zinc-950/50 backdrop-blur-md shrink-0">
        <div className="flex h-16 items-center justify-between px-6">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-600 shadow-lg shadow-indigo-500/20 ring-1 ring-white/10">
              <Bot className="w-5 h-5 text-white" />
            </div>
            <div className="flex flex-col">
              <span className="text-sm font-bold tracking-tight leading-none">RAG Chatbot <span className="text-indigo-500">Pro</span></span>
              <div className="mt-1 flex items-center gap-2">
                <div className={`h-1.5 w-1.5 rounded-full ${backend.status === 'up' ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]' : 'bg-red-500'}`} />
                <span className="text-[9px] font-bold uppercase tracking-widest text-zinc-500">{backend.status === 'up' ? backend.detail : 'Offline'}</span>
              </div>
            </div>
          </div>

          {/* Desktop menu */}
          <div className="hidden md:flex items-center gap-2">
            <button onClick={() => navTo('chat')} className={`flex items-center gap-2 rounded-lg px-4 py-2 text-xs font-bold uppercase tracking-wider transition-all border ${view === 'chat' ? 'bg-zinc-800 border-zinc-700 text-white' : 'border-transparent text-zinc-400 hover:text-zinc-200'}`}>
              <MessageSquare size={14} /> Chat
            </button>
            {currentUser && (
              <button onClick={() => navTo('profile')} className={`flex items-center gap-2 rounded-lg px-4 py-2 text-xs font-bold uppercase tracking-wider transition-all border ${view === 'profile' ? 'bg-zinc-800 border-zinc-700 text-white' : 'border-transparent text-zinc-400 hover:text-zinc-200'}`}>
                <UserCircle size={14} /> Profile
              </button>
            )}
            {!currentUser ? (
              <>
                <button onClick={() => navTo('register')} className={`flex items-center gap-2 rounded-lg px-4 py-2 text-xs font-bold uppercase tracking-wider transition-all border ${view === 'register' ? 'bg-zinc-800 border-zinc-700 text-white' : 'border-transparent text-zinc-400 hover:text-zinc-200'}`}>
                  <UserPlus size={14} /> Register
                </button>
                <button onClick={() => navTo('login')} className={`flex items-center gap-2 rounded-lg px-4 py-2 text-xs font-bold uppercase tracking-wider transition-all border ${view === 'login' ? 'bg-zinc-800 border-zinc-700 text-white' : 'border-transparent text-zinc-400 hover:text-zinc-200'}`}>
                  <LogIn size={14} /> Sign In
                </button>
              </>
            ) : (
              <button onClick={handleLogout} className="flex items-center gap-2 rounded-lg px-4 py-2 text-xs font-bold uppercase tracking-wider transition-all border border-transparent text-zinc-400 hover:text-zinc-200">
                <User size={14} /> {capitalize(currentUser.username)} (Sign Out)
              </button>
            )}
            <button onClick={() => navTo('debug')} className={`flex items-center gap-2 rounded-lg px-4 py-2 text-xs font-bold uppercase tracking-wider transition-all border ${view === 'debug' ? 'bg-zinc-800 border-zinc-700 text-indigo-400' : 'border-transparent text-zinc-400 hover:text-zinc-200'}`}>
              <Terminal size={14} /> Debug
            </button>
          </div>

          {/* Mobile hamburger */}
          <button onClick={() => setMobileMenuOpen(!mobileMenuOpen)} className="md:hidden flex h-10 w-10 items-center justify-center rounded-xl text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200 transition-all">
            {mobileMenuOpen ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>

        {/* Mobile dropdown */}
        {mobileMenuOpen && (
          <div className="md:hidden border-t border-zinc-900 bg-zinc-950/95 backdrop-blur-xl">
            <div className="flex flex-col p-3 gap-1">
              <button onClick={() => navTo('chat')} className={`flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-bold uppercase tracking-wider transition-all ${view === 'chat' ? 'bg-zinc-800 text-white' : 'text-zinc-400 hover:bg-zinc-900'}`}>
                <MessageSquare size={16} /> Chat
              </button>
              {currentUser && (
                <button onClick={() => navTo('profile')} className={`flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-bold uppercase tracking-wider transition-all ${view === 'profile' ? 'bg-zinc-800 text-white' : 'text-zinc-400 hover:bg-zinc-900'}`}>
                  <UserCircle size={16} /> Profile
                </button>
              )}
              {!currentUser ? (
                <>
                  <button onClick={() => navTo('register')} className={`flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-bold uppercase tracking-wider transition-all ${view === 'register' ? 'bg-zinc-800 text-white' : 'text-zinc-400 hover:bg-zinc-900'}`}>
                    <UserPlus size={16} /> Register
                  </button>
                  <button onClick={() => navTo('login')} className={`flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-bold uppercase tracking-wider transition-all ${view === 'login' ? 'bg-zinc-800 text-white' : 'text-zinc-400 hover:bg-zinc-900'}`}>
                    <LogIn size={16} /> Sign In
                  </button>
                </>
              ) : (
                <button onClick={() => { handleLogout(); setMobileMenuOpen(false); }} className="flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-bold uppercase tracking-wider text-zinc-400 hover:bg-zinc-900">
                  <User size={16} /> Sign Out
                </button>
              )}
              <button onClick={() => navTo('debug')} className={`flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-bold uppercase tracking-wider transition-all ${view === 'debug' ? 'bg-zinc-800 text-indigo-400' : 'text-zinc-400 hover:bg-zinc-900'}`}>
                <Terminal size={16} /> Debug
              </button>
            </div>
          </div>
        )}
      </nav>

      {/* Main Content */}
      <main className="flex-1 relative overflow-hidden flex flex-col">

        {/* ==================== CHAT VIEW ==================== */}
        {view === 'chat' && (
          <>
            <div className="flex-1 overflow-y-auto px-4 py-4">
              <div className="mx-auto max-w-3xl">
                {/* Quarter Navigation */}
                {currentUser && viewingQuarter && (
                  <div className="flex items-center justify-between mb-4 px-2">
                    <button onClick={() => navigateQuarter('prev')}
                      className="flex items-center gap-1 text-[10px] text-zinc-500 hover:text-zinc-300 uppercase tracking-wider font-bold transition-colors">
                      <ChevronLeft size={14} /> Prev
                    </button>
                    <div className="flex items-center gap-2">
                      <span className="text-[11px] font-bold text-zinc-400 uppercase tracking-widest">
                        {quarterLabel(viewingQuarter)}
                      </span>
                      {currentQuarter && (viewingQuarter.year !== currentQuarter.year || viewingQuarter.quarter !== currentQuarter.quarter) && (
                        <button onClick={goToCurrentQuarter}
                          className="text-[9px] text-indigo-400 hover:text-indigo-300 font-bold uppercase tracking-wider transition-colors ml-2">
                          Current →
                        </button>
                      )}
                    </div>
                    <button onClick={() => navigateQuarter('next')}
                      className="flex items-center gap-1 text-[10px] text-zinc-500 hover:text-zinc-300 uppercase tracking-wider font-bold transition-colors">
                      Next <ChevronRight size={14} />
                    </button>
                  </div>
                )}

                {messages.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-20 text-center">
                    <div className="mb-6 flex h-24 w-24 items-center justify-center rounded-full bg-zinc-900 ring-1 ring-zinc-800 shadow-inner">
                      <Bot className="w-12 h-12 text-zinc-800" />
                    </div>
                    <h2 className="text-2xl font-bold text-zinc-100">How can I help you today?</h2>
                    <p className="mt-2 max-w-md text-zinc-500 text-sm">Ask anything about your documents or provide a prompt to start.</p>
                    {!currentUser && <p className="mt-4 text-xs text-zinc-600">Sign in to save your chat history.</p>}
                    {currentUser && viewingQuarter && (
                      <p className="mt-4 text-xs text-zinc-600">No messages this quarter.</p>
                    )}
                  </div>
                ) : (
                  <>
                    {currentUser && messages.length > 0 && (
                      <div className="flex justify-end mb-4">
                        <button onClick={handleClearHistory} className="flex items-center gap-1.5 text-[10px] text-zinc-600 hover:text-red-400 uppercase tracking-wider font-bold transition-colors">
                          <Trash2 size={12} /> Clear View
                        </button>
                      </div>
                    )}
                    {groupMessagesByDate(messages).map((item, i) => {
                      if (item.type === 'date-header') {
                        return (
                          <div key={`date-${i}`} className="flex items-center gap-3 my-6">
                            <div className="flex-1 h-px bg-zinc-800/50" />
                            <span className="text-[10px] font-bold uppercase tracking-widest text-zinc-600 px-3 py-1 rounded-full bg-zinc-900/50 border border-zinc-800/50">
                              {formatDateHeader(item.date)}
                            </span>
                            <div className="flex-1 h-px bg-zinc-800/50" />
                          </div>
                        );
                      }
                      return <ChatMessage key={i} {...item} profilePic={profilePic} />;
                    })}
                  </>
                )}
                <div ref={messagesEndRef} className="h-4" />
              </div>
            </div>

            <div className="bg-gradient-to-t from-zinc-950 via-zinc-950 to-transparent pt-10 pb-6 shrink-0">
              <div className="mx-auto max-w-3xl px-4">
                <form onSubmit={handleSendMessage} className="relative flex items-center rounded-2xl border border-zinc-800 bg-zinc-900/50 p-1.5 shadow-2xl focus-within:border-indigo-500/50 transition-all ring-1 ring-white/5">
                  <input type="text" value={input} onChange={(e) => setInput(e.target.value)} disabled={isLoading}
                    placeholder={isLoading ? "Generating response..." : "Ask a question about your docs..."}
                    className="flex-1 bg-transparent px-4 py-3 text-sm outline-none placeholder:text-zinc-600" />
                  <div className="flex items-center gap-1">
                    {isLoading && (
                      <button type="button" onClick={handleStop} className="flex h-10 w-10 items-center justify-center rounded-xl text-zinc-400 hover:bg-zinc-800"><StopCircle size={20} /></button>
                    )}
                    <button type="submit" disabled={!input.trim() || isLoading}
                      className={`flex h-10 w-10 items-center justify-center rounded-xl transition-all ${!input.trim() || isLoading ? 'bg-zinc-800 text-zinc-600' : 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/20 hover:bg-indigo-500'}`}>
                      <Send size={18} />
                    </button>
                  </div>
                </form>
                {streamError && (
                  <div className="mt-3 flex items-center gap-2 rounded-xl bg-red-500/10 px-4 py-2 text-[11px] text-red-400 ring-1 ring-red-500/20">
                    <ShieldAlert size={12} /> <span className="font-bold uppercase tracking-wider">Stream Error:</span> <span className="truncate">{streamError}</span>
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

        {/* ==================== PROFILE VIEW ==================== */}
        {view === 'profile' && currentUser && (
          <div className="flex-1 overflow-y-auto p-6">
            <div className="mx-auto max-w-3xl space-y-8">
              {/* User Info Card */}
              <div className="rounded-3xl border border-zinc-900 bg-zinc-900/30 p-8 backdrop-blur-xl ring-1 ring-white/5">
                <div className="flex items-center gap-5">
                  <div className="relative group">
                    {profilePic ? (
                      <img src={profilePic} alt="Profile" className="h-20 w-20 rounded-2xl object-cover ring-1 ring-indigo-500/20" />
                    ) : (
                      <div className="flex h-20 w-20 items-center justify-center rounded-2xl bg-indigo-600/10 text-indigo-500 ring-1 ring-indigo-500/20">
                        <UserCircle size={48} />
                      </div>
                    )}
                    <button
                      onClick={() => profilePicRef.current?.click()}
                      className="absolute inset-0 flex items-center justify-center rounded-2xl bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer">
                      <Camera size={22} className="text-white" />
                    </button>
                    <input ref={profilePicRef} type="file" accept="image/*" className="hidden" onChange={handleProfilePicChange} />
                    {profilePic && (
                      <button onClick={removeProfilePic}
                        className="absolute -top-2 -right-2 flex h-6 w-6 items-center justify-center rounded-full bg-red-500/80 text-white opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-500">
                        <X size={14} />
                      </button>
                    )}
                  </div>
                  <div>
                    <h2 className="text-2xl font-bold">{capitalize(currentUser.username)}</h2>
                    <p className="text-sm text-zinc-500">{currentUser.email}</p>
                    <span className={`mt-1 inline-block rounded-full px-3 py-0.5 text-[10px] font-bold uppercase tracking-widest ${
                      currentUser.role === 'provider' ? 'bg-amber-500/10 text-amber-400 ring-1 ring-amber-500/20' : 'bg-indigo-500/10 text-indigo-400 ring-1 ring-indigo-500/20'
                    }`}>
                      {currentUser.role || 'user'}
                    </span>
                  </div>
                </div>
              </div>

              {/* ===== MY DAILY TASKS (Dashboard) ===== */}
              <div className="rounded-3xl border border-zinc-900 bg-zinc-900/30 p-8 backdrop-blur-xl ring-1 ring-white/5">
                <div className="flex items-center justify-between mb-6">
                  <h3 className="flex items-center gap-2 text-sm font-bold uppercase tracking-widest text-indigo-400">
                    <ClipboardList size={16} /> {currentUser.role === 'provider' ? 'Assigned Tasks' : 'My Daily Tasks'}
                  </h3>
                  <button onClick={loadTasks} className="text-[10px] text-zinc-500 hover:text-zinc-300 uppercase tracking-wider font-bold flex items-center gap-1 transition-colors">
                    <RefreshCw size={12} /> Refresh
                  </button>
                </div>

                {tasksLoading ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 size={24} className="animate-spin text-zinc-600" />
                  </div>
                ) : tasks.length === 0 ? (
                  <div className="text-center py-8">
                    <ClipboardList size={40} className="mx-auto text-zinc-800 mb-3" />
                    <p className="text-zinc-500 text-sm">
                      {currentUser.role === 'provider' ? "You haven't assigned any tasks yet." : "No tasks assigned to you yet."}
                    </p>
                    <p className="text-zinc-600 text-xs mt-1">
                      {currentUser.role === 'provider' ? "Use the form below to assign tasks to users." : "Your provider will assign tasks here."}
                    </p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {tasks.map(task => (
                      <div key={task.id}
                        className={`flex items-start gap-4 rounded-2xl border p-5 transition-all ${
                          task.status === 'completed'
                            ? 'border-emerald-900/30 bg-emerald-500/5'
                            : 'border-zinc-800 bg-zinc-950/50 hover:border-zinc-700'
                        }`}>
                        {currentUser.role === 'user' && (
                          <button onClick={() => handleToggleTask(task.id, task.status)}
                            className={`mt-0.5 shrink-0 transition-colors ${task.status === 'completed' ? 'text-emerald-400' : 'text-zinc-600 hover:text-indigo-400'}`}>
                            {task.status === 'completed' ? <CheckCircle2 size={22} /> : <Circle size={22} />}
                          </button>
                        )}
                        <div className="flex-1 min-w-0">
                          <p className={`text-sm font-medium ${task.status === 'completed' ? 'text-zinc-500 line-through' : 'text-zinc-100'}`}>
                            {task.title}
                          </p>
                          {task.description && (
                            <p className="text-xs text-zinc-500 mt-1">{task.description}</p>
                          )}
                          <div className="flex items-center gap-3 mt-2">
                            <span className="text-[10px] text-zinc-600 uppercase tracking-wider">
                              {currentUser.role === 'provider' ? `→ ${task.assigned_to_name}` : `From: ${task.assigned_by_name}`}
                            </span>
                            {task.due_date && (
                              <span className="flex items-center gap-1 text-[10px] text-zinc-600 uppercase tracking-wider">
                                <Calendar size={10} /> {task.due_date}
                              </span>
                            )}
                            <span className={`text-[10px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-full ${
                              task.status === 'completed'
                                ? 'bg-emerald-500/10 text-emerald-400'
                                : 'bg-amber-500/10 text-amber-400'
                            }`}>
                              {task.status}
                            </span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Provider: Assign Task Form (inline) */}
                {currentUser.role === 'provider' && (
                  <div className="mt-6 pt-6 border-t border-zinc-800/50">
                    <h4 className="flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-amber-400 mb-4">
                      <Plus size={14} /> Assign a New Task
                    </h4>
                    <form onSubmit={handleCreateTask} className="space-y-3">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        <input value={newTask.title} onChange={(e) => setNewTask({...newTask, title: e.target.value})}
                          className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-4 py-2.5 text-sm focus:border-indigo-500/50 outline-none transition-all placeholder:text-zinc-700"
                          placeholder="Task title" required />
                        <select value={newTask.assigned_to} onChange={(e) => setNewTask({...newTask, assigned_to: e.target.value})}
                          className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-4 py-2.5 text-sm focus:border-indigo-500/50 outline-none transition-all text-zinc-300" required>
                          <option value="">Assign to...</option>
                          {usersList.map(u => (
                            <option key={u.id} value={u.id}>{u.username} ({u.email})</option>
                          ))}
                        </select>
                      </div>
                      <textarea value={newTask.description} onChange={(e) => setNewTask({...newTask, description: e.target.value})}
                        className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-4 py-2.5 text-sm focus:border-indigo-500/50 outline-none transition-all placeholder:text-zinc-700 resize-none h-16"
                        placeholder="Optional description..." />
                      <div className="flex gap-3">
                        <input type="date" value={newTask.due_date} onChange={(e) => setNewTask({...newTask, due_date: e.target.value})}
                          className="rounded-xl border border-zinc-800 bg-zinc-950 px-4 py-2.5 text-sm focus:border-indigo-500/50 outline-none transition-all text-zinc-300" />
                        <button type="submit"
                          className="flex-1 rounded-xl bg-amber-600 py-2.5 text-sm font-bold text-white shadow-lg shadow-amber-500/20 hover:bg-amber-500 transition-all flex items-center justify-center gap-2">
                          <Plus size={14} /> Assign Task
                        </button>
                      </div>
                      {taskError && (
                        <div className="flex items-center gap-2 rounded-xl bg-red-500/10 px-3 py-2 text-xs text-red-400 ring-1 ring-red-500/20">
                          <ShieldAlert size={14} /> <span>{taskError}</span>
                        </div>
                      )}
                    </form>
                  </div>
                )}
              </div>

              {/* ===== SECTION A: Identifying Information ===== */}
              <div className="rounded-3xl border border-zinc-900 bg-zinc-900/30 p-8 backdrop-blur-xl ring-1 ring-white/5">
                <h3 className="flex items-center gap-2 text-sm font-bold uppercase tracking-widest text-indigo-400 mb-6">
                  <UserCircle size={16} /> A. Identifying Information
                </h3>
                <div className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-1">
                      <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 ml-1">Full Name</label>
                      <input value={profileData.fullName} onChange={(e) => updateProfile('fullName', e.target.value)}
                        className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-4 py-3 text-sm focus:border-indigo-500/50 outline-none transition-all placeholder:text-zinc-700"
                        placeholder="Legal full name" />
                    </div>
                    <div className="space-y-1">
                      <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 ml-1">Preferred Name</label>
                      <input value={profileData.preferredName} onChange={(e) => updateProfile('preferredName', e.target.value)}
                        className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-4 py-3 text-sm focus:border-indigo-500/50 outline-none transition-all placeholder:text-zinc-700"
                        placeholder="What you'd like to be called" />
                    </div>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-1">
                      <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 ml-1">Pronouns</label>
                      <select value={profileData.pronouns} onChange={(e) => updateProfile('pronouns', e.target.value)}
                        className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-4 py-3 text-sm focus:border-indigo-500/50 outline-none transition-all text-zinc-300">
                        <option value="">Select pronouns...</option>
                        <option value="he/him">He / Him</option>
                        <option value="she/her">She / Her</option>
                        <option value="they/them">They / Them</option>
                        <option value="he/they">He / They</option>
                        <option value="she/they">She / They</option>
                        <option value="other">Other</option>
                      </select>
                    </div>
                    <div className="space-y-1">
                      <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 ml-1">Date of Birth</label>
                      <input type="date" value={profileData.dob} onChange={(e) => updateProfile('dob', e.target.value)}
                        className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-4 py-3 text-sm focus:border-indigo-500/50 outline-none transition-all text-zinc-300" />
                    </div>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-1">
                      <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 ml-1">Phone</label>
                      <input type="tel" value={profileData.contactPhone} onChange={(e) => updateProfile('contactPhone', e.target.value)}
                        className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-4 py-3 text-sm focus:border-indigo-500/50 outline-none transition-all placeholder:text-zinc-700"
                        placeholder="+1 (555) 000-0000" />
                    </div>
                    <div className="space-y-1">
                      <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 ml-1">Email</label>
                      <input type="email" value={profileData.contactEmail} onChange={(e) => updateProfile('contactEmail', e.target.value)}
                        className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-4 py-3 text-sm focus:border-indigo-500/50 outline-none transition-all placeholder:text-zinc-700"
                        placeholder="personal@email.com" />
                    </div>
                  </div>
                  <div className="border-t border-zinc-800/50 pt-4 mt-2">
                    <p className="text-[10px] font-bold uppercase tracking-widest text-zinc-600 mb-3 ml-1">Emergency Contact</p>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div className="space-y-1">
                        <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 ml-1">Name</label>
                        <input value={profileData.emergencyName} onChange={(e) => updateProfile('emergencyName', e.target.value)}
                          className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-4 py-3 text-sm focus:border-indigo-500/50 outline-none transition-all placeholder:text-zinc-700"
                          placeholder="Emergency contact name" />
                      </div>
                      <div className="space-y-1">
                        <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 ml-1">Relationship</label>
                        <input value={profileData.emergencyRelation} onChange={(e) => updateProfile('emergencyRelation', e.target.value)}
                          className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-4 py-3 text-sm focus:border-indigo-500/50 outline-none transition-all placeholder:text-zinc-700"
                          placeholder="e.g. Parent, Sibling" />
                      </div>
                      <div className="space-y-1">
                        <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 ml-1">Phone</label>
                        <input type="tel" value={profileData.emergencyPhone} onChange={(e) => updateProfile('emergencyPhone', e.target.value)}
                          className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-4 py-3 text-sm focus:border-indigo-500/50 outline-none transition-all placeholder:text-zinc-700"
                          placeholder="+1 (555) 000-0000" />
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* ===== SECTION B: Parent/Guardian Information ===== */}
              <div className="rounded-3xl border border-zinc-900 bg-zinc-900/30 p-8 backdrop-blur-xl ring-1 ring-white/5">
                <h3 className="flex items-center gap-2 text-sm font-bold uppercase tracking-widest text-indigo-400 mb-6">
                  <User size={16} /> B. Parent / Guardian Information
                </h3>

                {/* Parent / Guardian 1 */}
                <div className="mb-8">
                  <p className="text-xs font-bold text-zinc-400 mb-4 px-1 border-l-2 border-indigo-500 pl-3">Parent / Guardian 1</p>
                  <div className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="space-y-1">
                        <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 ml-1">Full Name</label>
                        <input value={profileData.parent1FullName} onChange={(e) => updateProfile('parent1FullName', e.target.value)}
                          className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-4 py-3 text-sm focus:border-indigo-500/50 outline-none transition-all placeholder:text-zinc-700"
                          placeholder="Legal full name" />
                      </div>
                      <div className="space-y-1">
                        <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 ml-1">Preferred Name</label>
                        <input value={profileData.parent1PreferredName} onChange={(e) => updateProfile('parent1PreferredName', e.target.value)}
                          className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-4 py-3 text-sm focus:border-indigo-500/50 outline-none transition-all placeholder:text-zinc-700"
                          placeholder="Preferred name" />
                      </div>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="space-y-1">
                        <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 ml-1">Pronouns</label>
                        <select value={profileData.parent1Pronouns} onChange={(e) => updateProfile('parent1Pronouns', e.target.value)}
                          className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-4 py-3 text-sm focus:border-indigo-500/50 outline-none transition-all text-zinc-300">
                          <option value="">Select pronouns...</option>
                          <option value="he/him">He / Him</option>
                          <option value="she/her">She / Her</option>
                          <option value="they/them">They / Them</option>
                          <option value="other">Other</option>
                        </select>
                      </div>
                      <div className="space-y-1">
                        <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 ml-1">Date of Birth</label>
                        <input type="date" value={profileData.parent1Dob} onChange={(e) => updateProfile('parent1Dob', e.target.value)}
                          className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-4 py-3 text-sm focus:border-indigo-500/50 outline-none transition-all text-zinc-300" />
                      </div>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="space-y-1">
                        <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 ml-1">Phone</label>
                        <input type="tel" value={profileData.parent1ContactPhone} onChange={(e) => updateProfile('parent1ContactPhone', e.target.value)}
                          className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-4 py-3 text-sm focus:border-indigo-500/50 outline-none transition-all placeholder:text-zinc-700"
                          placeholder="+1 (555) 000-0000" />
                      </div>
                      <div className="space-y-1">
                        <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 ml-1">Email</label>
                        <input type="email" value={profileData.parent1ContactEmail} onChange={(e) => updateProfile('parent1ContactEmail', e.target.value)}
                          className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-4 py-3 text-sm focus:border-indigo-500/50 outline-none transition-all placeholder:text-zinc-700"
                          placeholder="parent@email.com" />
                      </div>
                    </div>
                    <div className="border-t border-zinc-800/50 pt-4">
                      <p className="text-[10px] font-bold uppercase tracking-widest text-zinc-600 mb-3 ml-1">Emergency Contact</p>
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div className="space-y-1">
                          <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 ml-1">Name</label>
                          <input value={profileData.parent1EmergencyName} onChange={(e) => updateProfile('parent1EmergencyName', e.target.value)}
                            className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-4 py-3 text-sm focus:border-indigo-500/50 outline-none transition-all placeholder:text-zinc-700"
                            placeholder="Emergency contact" />
                        </div>
                        <div className="space-y-1">
                          <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 ml-1">Relationship</label>
                          <input value={profileData.parent1EmergencyRelation} onChange={(e) => updateProfile('parent1EmergencyRelation', e.target.value)}
                            className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-4 py-3 text-sm focus:border-indigo-500/50 outline-none transition-all placeholder:text-zinc-700"
                            placeholder="Relationship" />
                        </div>
                        <div className="space-y-1">
                          <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 ml-1">Phone</label>
                          <input type="tel" value={profileData.parent1EmergencyPhone} onChange={(e) => updateProfile('parent1EmergencyPhone', e.target.value)}
                            className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-4 py-3 text-sm focus:border-indigo-500/50 outline-none transition-all placeholder:text-zinc-700"
                            placeholder="+1 (555) 000-0000" />
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Parent / Guardian 2 */}
                <div>
                  <p className="text-xs font-bold text-zinc-400 mb-4 px-1 border-l-2 border-amber-500 pl-3">Parent / Guardian 2 <span className="text-zinc-600 font-normal">(optional)</span></p>
                  <div className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="space-y-1">
                        <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 ml-1">Full Name</label>
                        <input value={profileData.parent2FullName} onChange={(e) => updateProfile('parent2FullName', e.target.value)}
                          className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-4 py-3 text-sm focus:border-indigo-500/50 outline-none transition-all placeholder:text-zinc-700"
                          placeholder="Legal full name" />
                      </div>
                      <div className="space-y-1">
                        <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 ml-1">Preferred Name</label>
                        <input value={profileData.parent2PreferredName} onChange={(e) => updateProfile('parent2PreferredName', e.target.value)}
                          className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-4 py-3 text-sm focus:border-indigo-500/50 outline-none transition-all placeholder:text-zinc-700"
                          placeholder="Preferred name" />
                      </div>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="space-y-1">
                        <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 ml-1">Pronouns</label>
                        <select value={profileData.parent2Pronouns} onChange={(e) => updateProfile('parent2Pronouns', e.target.value)}
                          className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-4 py-3 text-sm focus:border-indigo-500/50 outline-none transition-all text-zinc-300">
                          <option value="">Select pronouns...</option>
                          <option value="he/him">He / Him</option>
                          <option value="she/her">She / Her</option>
                          <option value="they/them">They / Them</option>
                          <option value="other">Other</option>
                        </select>
                      </div>
                      <div className="space-y-1">
                        <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 ml-1">Date of Birth</label>
                        <input type="date" value={profileData.parent2Dob} onChange={(e) => updateProfile('parent2Dob', e.target.value)}
                          className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-4 py-3 text-sm focus:border-indigo-500/50 outline-none transition-all text-zinc-300" />
                      </div>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="space-y-1">
                        <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 ml-1">Phone</label>
                        <input type="tel" value={profileData.parent2ContactPhone} onChange={(e) => updateProfile('parent2ContactPhone', e.target.value)}
                          className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-4 py-3 text-sm focus:border-indigo-500/50 outline-none transition-all placeholder:text-zinc-700"
                          placeholder="+1 (555) 000-0000" />
                      </div>
                      <div className="space-y-1">
                        <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 ml-1">Email</label>
                        <input type="email" value={profileData.parent2ContactEmail} onChange={(e) => updateProfile('parent2ContactEmail', e.target.value)}
                          className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-4 py-3 text-sm focus:border-indigo-500/50 outline-none transition-all placeholder:text-zinc-700"
                          placeholder="parent@email.com" />
                      </div>
                    </div>
                    <div className="border-t border-zinc-800/50 pt-4">
                      <p className="text-[10px] font-bold uppercase tracking-widest text-zinc-600 mb-3 ml-1">Emergency Contact</p>
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div className="space-y-1">
                          <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 ml-1">Name</label>
                          <input value={profileData.parent2EmergencyName} onChange={(e) => updateProfile('parent2EmergencyName', e.target.value)}
                            className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-4 py-3 text-sm focus:border-indigo-500/50 outline-none transition-all placeholder:text-zinc-700"
                            placeholder="Emergency contact" />
                        </div>
                        <div className="space-y-1">
                          <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 ml-1">Relationship</label>
                          <input value={profileData.parent2EmergencyRelation} onChange={(e) => updateProfile('parent2EmergencyRelation', e.target.value)}
                            className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-4 py-3 text-sm focus:border-indigo-500/50 outline-none transition-all placeholder:text-zinc-700"
                            placeholder="Relationship" />
                        </div>
                        <div className="space-y-1">
                          <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 ml-1">Phone</label>
                          <input type="tel" value={profileData.parent2EmergencyPhone} onChange={(e) => updateProfile('parent2EmergencyPhone', e.target.value)}
                            className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-4 py-3 text-sm focus:border-indigo-500/50 outline-none transition-all placeholder:text-zinc-700"
                            placeholder="+1 (555) 000-0000" />
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* ===== SECTION C: Consent & Logistics ===== */}
              <div className="rounded-3xl border border-zinc-900 bg-zinc-900/30 p-8 backdrop-blur-xl ring-1 ring-white/5">
                <h3 className="flex items-center gap-2 text-sm font-bold uppercase tracking-widest text-indigo-400 mb-6">
                  <ShieldCheck size={16} /> C. Consent & Logistics
                </h3>
                <div className="space-y-5">
                  <label className="flex items-start gap-3 group cursor-pointer">
                    <div className="relative flex h-5 w-5 mt-0.5 items-center justify-center shrink-0">
                      <input type="checkbox" className="peer h-full w-full cursor-pointer appearance-none rounded border border-zinc-700 bg-zinc-950 checked:bg-indigo-600 checked:border-indigo-500 transition-all"
                        checked={profileData.consentAcknowledged} onChange={(e) => updateProfile('consentAcknowledged', e.target.checked)} />
                      <Check size={14} className="pointer-events-none absolute text-white opacity-0 peer-checked:opacity-100 transition-opacity" />
                    </div>
                    <div>
                      <span className="text-sm font-medium text-zinc-300 group-hover:text-white transition-colors">Informed Consent Acknowledged</span>
                      <p className="text-xs text-zinc-600 mt-0.5">I have read and understood the informed consent for treatment.</p>
                    </div>
                  </label>

                  <label className="flex items-start gap-3 group cursor-pointer">
                    <div className="relative flex h-5 w-5 mt-0.5 items-center justify-center shrink-0">
                      <input type="checkbox" className="peer h-full w-full cursor-pointer appearance-none rounded border border-zinc-700 bg-zinc-950 checked:bg-indigo-600 checked:border-indigo-500 transition-all"
                        checked={profileData.confidentialityExplained} onChange={(e) => updateProfile('confidentialityExplained', e.target.checked)} />
                      <Check size={14} className="pointer-events-none absolute text-white opacity-0 peer-checked:opacity-100 transition-opacity" />
                    </div>
                    <div>
                      <span className="text-sm font-medium text-zinc-300 group-hover:text-white transition-colors">Confidentiality Limits Explained</span>
                      <p className="text-xs text-zinc-600 mt-0.5">I understand confidentiality limits including harm to self/others, abuse, and court orders.</p>
                    </div>
                  </label>

                  <div className="border-t border-zinc-800/50 pt-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="space-y-1">
                        <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 ml-1">Session Format</label>
                        <select value={profileData.sessionFormat} onChange={(e) => updateProfile('sessionFormat', e.target.value)}
                          className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-4 py-3 text-sm focus:border-indigo-500/50 outline-none transition-all text-zinc-300">
                          <option value="">Select format...</option>
                          <option value="in-person">In-Person</option>
                          <option value="telehealth">Telehealth</option>
                          <option value="hybrid">Hybrid (Both)</option>
                        </select>
                      </div>
                      <div className="space-y-1">
                        <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 ml-1">Payment / Insurance Info</label>
                        <input value={profileData.paymentInfo} onChange={(e) => updateProfile('paymentInfo', e.target.value)}
                          className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-4 py-3 text-sm focus:border-indigo-500/50 outline-none transition-all placeholder:text-zinc-700"
                          placeholder="Insurance provider or self-pay" />
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Save Profile Button */}
              <button onClick={saveProfileData}
                className={`w-full rounded-2xl py-4 text-sm font-bold text-white shadow-lg transition-all flex items-center justify-center gap-2 ${
                  profileSaved
                    ? 'bg-emerald-600 shadow-emerald-500/20'
                    : 'bg-indigo-600 shadow-indigo-500/20 hover:bg-indigo-500'
                }`}>
                {profileSaved ? <><Check size={18} /> Profile Saved!</> : <><Save size={18} /> Save Profile</>}
              </button>

            </div>
          </div>
        )}

        {/* ==================== REGISTER VIEW ==================== */}
        {view === 'register' && (
          <div className="flex-1 flex items-center justify-center p-6 overflow-y-auto">
            <div className="w-full max-w-md space-y-6 rounded-3xl border border-zinc-900 bg-zinc-900/30 p-10 backdrop-blur-xl ring-1 ring-white/5 shadow-2xl">
              <div className="text-center">
                <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-indigo-600/10 text-indigo-500 ring-1 ring-indigo-500/20">
                  <UserPlus size={32} />
                </div>
                <h2 className="text-3xl font-bold tracking-tight">Create Account</h2>
                <p className="mt-2 text-sm text-zinc-500">Sign up to get started with RAG Chatbot Pro.</p>
              </div>

              <button onClick={handleGoogleSignIn}
                className="w-full flex items-center justify-center gap-3 rounded-xl border border-zinc-800 bg-zinc-950 py-3.5 text-sm font-medium text-zinc-300 hover:bg-zinc-900 hover:text-white transition-all">
                <svg width="18" height="18" viewBox="0 0 24 24">
                  <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/>
                  <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                  <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                  <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
                </svg>
                Sign up with Google
              </button>
              <div id="google-signin-fallback" className="w-full"></div>

              <div className="flex items-center gap-3">
                <div className="flex-1 h-px bg-zinc-800"></div>
                <span className="text-[10px] font-bold uppercase tracking-widest text-zinc-600">or</span>
                <div className="flex-1 h-px bg-zinc-800"></div>
              </div>

              <form onSubmit={handleRegister} className="space-y-4">
                <div className="space-y-1">
                  <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 ml-1">Username</label>
                  <input value={regForm.username} onChange={(e) => setRegForm({...regForm, username: e.target.value})}
                    className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-4 py-3 text-sm focus:border-indigo-500/50 outline-none transition-all placeholder:text-zinc-700"
                    placeholder="Choose a username" required />
                </div>

                <div className="space-y-1">
                  <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 ml-1">Email Address</label>
                  <input type="email" value={regForm.email} onChange={(e) => setRegForm({...regForm, email: e.target.value})}
                    className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-4 py-3 text-sm focus:border-indigo-500/50 outline-none transition-all placeholder:text-zinc-700"
                    placeholder="name@example.com" required />
                </div>

                <div className="space-y-1">
                  <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 ml-1 flex justify-between items-center">
                    Password <span className="text-[9px] text-indigo-400 normal-case italic">use symbols & numbers</span>
                  </label>
                  <div className="relative">
                    <input type={showPassword ? "text" : "password"} value={regForm.password}
                      onChange={(e) => setRegForm({...regForm, password: e.target.value})}
                      className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-4 py-3 pr-12 text-sm focus:border-indigo-500/50 outline-none transition-all"
                      placeholder="Min. 8 characters" required />
                    <button type="button" onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-600 hover:text-zinc-400 transition-colors">
                      {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  </div>
                  <div className="flex items-center gap-2 mt-1.5 ml-1">
                    <button type="button" onClick={generateStrongPassword} className="text-[10px] text-indigo-400 hover:text-indigo-300 font-medium transition-colors">
                      Generate strong password
                    </button>
                    {suggestedPassword && (
                      <div className="flex items-center gap-2">
                        <code className="text-[10px] text-emerald-500/80 font-mono bg-zinc-900 px-2 py-0.5 rounded">{suggestedPassword}</code>
                        <button type="button" onClick={useSuggestedPassword} className="text-[10px] text-indigo-400 hover:text-indigo-300 font-bold uppercase transition-colors">Use</button>
                      </div>
                    )}
                  </div>
                </div>

                <div className="space-y-1">
                  <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 ml-1">Confirm Password</label>
                  <input type="password" value={regForm.confirmPassword} onChange={(e) => setRegForm({...regForm, confirmPassword: e.target.value})}
                    className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-4 py-3 text-sm focus:border-indigo-500/50 outline-none transition-all"
                    placeholder="Repeat your password" required />
                </div>

                <div className="space-y-1">
                  <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 ml-1">Age</label>
                  <input type="number" value={regForm.age} onChange={(e) => setRegForm({...regForm, age: e.target.value})}
                    className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-4 py-3 text-sm focus:border-indigo-500/50 outline-none transition-all placeholder:text-zinc-700"
                    placeholder="Must be 13 or older" min="13" max="120" required />
                </div>

                <div className="space-y-1">
                  <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 ml-1">
                    Phone Number <span className="text-zinc-700">(optional)</span>
                  </label>
                  <input type="tel" value={regForm.phone} onChange={(e) => setRegForm({...regForm, phone: e.target.value})}
                    className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-4 py-3 text-sm focus:border-indigo-500/50 outline-none transition-all placeholder:text-zinc-700"
                    placeholder="+1234567890" />
                </div>

                <div className="space-y-2 pt-2 border-t border-zinc-800/50">
                  <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 ml-1">Account Role</label>
                  <div className="flex gap-6 px-1">
                    <label className="flex items-center gap-2.5 group cursor-pointer">
                      <div className="relative flex h-5 w-5 items-center justify-center">
                        <input type="checkbox" className="peer h-full w-full cursor-pointer appearance-none rounded border border-zinc-700 bg-zinc-950 checked:bg-indigo-600 checked:border-indigo-500 transition-all"
                          checked={role === 'user'} onChange={() => setRole('user')} />
                        <Check size={14} className="pointer-events-none absolute text-white opacity-0 peer-checked:opacity-100 transition-opacity" />
                      </div>
                      <span className="text-sm font-medium text-zinc-400 group-hover:text-zinc-200 transition-colors">User</span>
                    </label>
                    <label className="flex items-center gap-2.5 group cursor-pointer">
                      <div className="relative flex h-5 w-5 items-center justify-center">
                        <input type="checkbox" className="peer h-full w-full cursor-pointer appearance-none rounded border border-zinc-700 bg-zinc-950 checked:bg-indigo-600 checked:border-indigo-500 transition-all"
                          checked={role === 'provider'} onChange={() => setRole('provider')} />
                        <Check size={14} className="pointer-events-none absolute text-white opacity-0 peer-checked:opacity-100 transition-opacity" />
                      </div>
                      <span className="text-sm font-medium text-zinc-400 group-hover:text-zinc-200 transition-colors">Provider</span>
                    </label>
                  </div>
                </div>

                {regError && (
                  <div className="flex items-center gap-2 rounded-xl bg-red-500/10 px-4 py-2.5 text-xs text-red-400 ring-1 ring-red-500/20">
                    <ShieldAlert size={14} /> <span>{regError}</span>
                  </div>
                )}

                <button type="submit" disabled={regLoading}
                  className="w-full rounded-xl bg-indigo-600 py-4 text-sm font-bold text-white shadow-lg shadow-indigo-500/20 hover:bg-indigo-500 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2">
                  {regLoading ? <><Loader2 size={16} className="animate-spin" /> Creating Account...</> : 'Sign Up Now'}
                </button>
              </form>

              <p className="text-center text-sm text-zinc-500">
                Already have an account?{' '}
                <button onClick={() => setView('login')} className="text-indigo-400 hover:text-indigo-300 font-medium transition-colors">Sign In</button>
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
            <div className="w-full max-w-md space-y-6 rounded-3xl border border-zinc-900 bg-zinc-900/30 p-10 backdrop-blur-xl ring-1 ring-white/5 shadow-2xl">
              <div className="text-center">
                <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-indigo-600/10 text-indigo-500 ring-1 ring-indigo-500/20">
                  <LogIn size={32} />
                </div>
                <h2 className="text-3xl font-bold tracking-tight">Welcome Back</h2>
                <p className="mt-2 text-sm text-zinc-500">Sign in to your account to continue.</p>
              </div>

              <button onClick={handleGoogleSignIn}
                className="w-full flex items-center justify-center gap-3 rounded-xl border border-zinc-800 bg-zinc-950 py-3.5 text-sm font-medium text-zinc-300 hover:bg-zinc-900 hover:text-white transition-all">
                <svg width="18" height="18" viewBox="0 0 24 24">
                  <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/>
                  <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                  <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                  <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
                </svg>
                Sign in with Google
              </button>
              <div id="google-signin-fallback" className="w-full"></div>

              <div className="flex items-center gap-3">
                <div className="flex-1 h-px bg-zinc-800"></div>
                <span className="text-[10px] font-bold uppercase tracking-widest text-zinc-600">or</span>
                <div className="flex-1 h-px bg-zinc-800"></div>
              </div>

              <form onSubmit={handleLogin} className="space-y-4">
                <div className="space-y-1">
                  <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 ml-1">Email Address</label>
                  <input type="email" value={loginForm.email} onChange={(e) => setLoginForm({...loginForm, email: e.target.value})}
                    className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-4 py-3 text-sm focus:border-indigo-500/50 outline-none transition-all placeholder:text-zinc-700"
                    placeholder="name@example.com" required />
                </div>
                <div className="space-y-1">
                  <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 ml-1">Password</label>
                  <div className="relative">
                    <input type={showPassword ? "text" : "password"} value={loginForm.password}
                      onChange={(e) => setLoginForm({...loginForm, password: e.target.value})}
                      className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-4 py-3 pr-12 text-sm focus:border-indigo-500/50 outline-none transition-all"
                      placeholder="Enter your password" required />
                    <button type="button" onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-600 hover:text-zinc-400 transition-colors">
                      {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  </div>
                </div>
                {loginError && (
                  <div className="flex items-center gap-2 rounded-xl bg-red-500/10 px-4 py-2.5 text-xs text-red-400 ring-1 ring-red-500/20">
                    <ShieldAlert size={14} /> <span>{loginError}</span>
                  </div>
                )}
                <button type="submit" disabled={loginLoading}
                  className="w-full rounded-xl bg-indigo-600 py-4 text-sm font-bold text-white shadow-lg shadow-indigo-500/20 hover:bg-indigo-500 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2">
                  {loginLoading ? <><Loader2 size={16} className="animate-spin" /> Signing In...</> : 'Sign In'}
                </button>
              </form>

              <p className="text-center text-sm text-zinc-500">
                Don't have an account?{' '}
                <button onClick={() => setView('register')} className="text-indigo-400 hover:text-indigo-300 font-medium transition-colors">Sign Up</button>
              </p>
            </div>
          </div>
        )}

        {/* ==================== VERIFY PIN VIEW ==================== */}
        {view === 'verify' && (
          <div className="flex-1 flex items-center justify-center p-6 overflow-y-auto">
            <div className="w-full max-w-md space-y-6 rounded-3xl border border-zinc-900 bg-zinc-900/30 p-10 backdrop-blur-xl ring-1 ring-white/5 shadow-2xl">
              <button onClick={() => setView('register')} className="flex items-center gap-1.5 text-xs text-zinc-500 hover:text-zinc-300 transition-colors">
                <ArrowLeft size={14} /> Back
              </button>
              <div className="text-center">
                <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-indigo-600/10 text-indigo-500 ring-1 ring-indigo-500/20">
                  <Mail size={32} />
                </div>
                <h2 className="text-3xl font-bold tracking-tight">Check Your Email</h2>
                <p className="mt-2 text-sm text-zinc-500">We sent a 6-digit code to <span className="text-indigo-400 font-medium">{verifyEmail}</span></p>
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
                  <div className="flex justify-center gap-3">
                    {pinDigits.map((digit, i) => (
                      <input key={i} ref={(el) => (pinRefs.current[i] = el)} type="text" inputMode="numeric" maxLength={1}
                        value={digit} onChange={(e) => handlePinChange(i, e.target.value)} onKeyDown={(e) => handlePinKeyDown(i, e)}
                        onPaste={i === 0 ? handlePinPaste : undefined}
                        className={`h-14 w-12 rounded-xl border text-center text-xl font-bold outline-none transition-all ${
                          digit ? 'border-indigo-500 bg-indigo-500/10 text-indigo-400' : 'border-zinc-800 bg-zinc-950 text-zinc-100'
                        } focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20`} />
                    ))}
                  </div>
                  {verifyError && (
                    <div className="flex items-center gap-2 rounded-xl bg-red-500/10 px-4 py-2.5 text-xs text-red-400 ring-1 ring-red-500/20">
                      <ShieldAlert size={14} /> <span>{verifyError}</span>
                    </div>
                  )}
                  <button onClick={handleVerifyPin} disabled={verifyLoading || pinDigits.join('').length !== 6}
                    className="w-full rounded-xl bg-indigo-600 py-4 text-sm font-bold text-white shadow-lg shadow-indigo-500/20 hover:bg-indigo-500 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2">
                    {verifyLoading ? <><Loader2 size={16} className="animate-spin" /> Verifying...</> : 'Verify Email'}
                  </button>
                  <div className="text-center">
                    <p className="text-sm text-zinc-500">
                      Didn't receive a code?{' '}
                      <button onClick={handleResendPin} disabled={resendLoading}
                        className="text-indigo-400 hover:text-indigo-300 font-medium transition-colors disabled:opacity-50 inline-flex items-center gap-1">
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
                    <p className="text-sm font-mono text-zinc-300">{currentUser ? `${currentUser.username} (${currentUser.role})` : 'Not signed in'}</p>
                  </div>
                  <div className="p-4 rounded-xl bg-zinc-950 border border-zinc-800">
                    <p className="text-[10px] text-zinc-500 uppercase mb-1">Auth Status</p>
                    <p className={`text-sm font-mono ${currentUser ? 'text-emerald-400' : 'text-amber-400'}`}>{currentUser ? 'AUTHENTICATED' : 'GUEST'}</p>
                  </div>
                </div>
                <div className="mt-6">
                  <p className="text-[10px] text-zinc-500 uppercase mb-2">System Capabilities</p>
                  <div className="flex flex-wrap gap-2">
                    {['SSE STREAMING', 'BITNET 1.58B', 'CHROMA DB', 'GMAIL SMTP', 'JWT AUTH', 'GOOGLE OAUTH', 'CHAT HISTORY', 'TASK MGMT'].map(cap => (
                      <span key={cap} className="rounded-md bg-zinc-900 px-2 py-1 text-[10px] font-bold text-zinc-400 border border-zinc-800">{cap}</span>
                    ))}
                  </div>
                </div>
                <button onClick={() => window.location.reload()}
                  className="mt-8 w-full py-3 rounded-xl bg-zinc-800 hover:bg-zinc-700 text-xs font-bold uppercase tracking-widest transition-all text-zinc-300">
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