<script>
  let showModal = false;
  let step = 1;
  
  let email = ''; 
  let verificationCode = '';
  let password = '';
  let confirmPassword = '';
  let accountRole = 'user';
  let error = '';
  let success = '';
  let loading = false;
  let timeRemaining = 0;
  let timerInterval = null;
  
  // Start as OFFLINE until we verify the backend is awake
  let status = "OFFLINE"; 

  // --- NEW: Health Check Logic ---
  // This runs as soon as the page loads to check if your FastAPI is up
  import { onMount } from 'svelte';
  
  async function checkBackendHealth() {
    try {
      const res = await fetch('http://localhost:8000/health');
      if (res.ok) {
        status = "ONLINE";
      } else {
        status = "OFFLINE";
      }
    } catch (e) {
      status = "OFFLINE";
    }
  }

  onMount(() => {
    checkBackendHealth();
    // Re-check every 30 seconds
    const healthInterval = setInterval(checkBackendHealth, 30000);
    return () => clearInterval(healthInterval);
  });

  // --- URL Param Handling ---
  if (typeof window !== 'undefined') {
    const urlParams = new URLSearchParams(window.location.hash.split('?')[1]);
    const emailParam = urlParams.get('email');
    if (emailParam) {
      email = decodeURIComponent(emailParam);
      step = 2;
      showModal = true;
      startTimer(300);
    }
  }
  
  function startTimer(seconds) {
    timeRemaining = seconds;
    if (timerInterval) clearInterval(timerInterval);
    timerInterval = setInterval(() => {
      timeRemaining--;
      if (timeRemaining <= 0) {
        clearInterval(timerInterval);
        timerInterval = null;
      }
    }, 1000);
  }
  
  function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return mins + ':' + (secs < 10 ? '0' : '') + secs;
  }
  
  async function handleSendCode() {
    error = '';
    if (!email) {
      error = 'Please enter your email';
      return;
    }
    loading = true;
    try {
      const response = await fetch('http://localhost:8000/api/send-verification-code', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email })
      });
      const data = await response.json();
      if (response.ok) {
        success = 'Code sent! Check your terminal.';
        step = 2;
        showModal = true;
        startTimer(300);
      } else {
        error = data.detail || 'Failed to send code';
      }
    } catch (err) {
      error = 'Backend is not responding. Check your terminal for errors.';
    } finally {
      loading = false;
    }
  }
  
  async function handleVerifyCode() {
    error = '';
    loading = true;
    try {
      const response = await fetch('http://localhost:8000/api/verify-code', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email, code: verificationCode.trim() })
      });
      if (response.ok) {
        success = 'Email verified!';
        step = 3; // Moves you to the Password/Role screen
        showModal = false;
        if (timerInterval) clearInterval(timerInterval);
      } else {
        const data = await response.json();
        error = data.detail || 'Invalid code';
      }
    } catch (err) {
      error = 'Network error during verification.';
    } finally {
      loading = false;
    }
  }
  
  async function handleRegister() {
    error = '';
    if (password !== confirmPassword) {
      error = 'Passwords do not match';
      return;
    }
    loading = true;
    try {
      const response = await fetch('http://localhost:8000/api/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: email,
          password: password,
          role: accountRole
        })
      });
      const data = await response.json();
      if (response.ok) {
        localStorage.setItem('userEmail', email);
        localStorage.setItem('token', data.access_token);
        localStorage.setItem('isLoggedIn', 'true');
        status = "ONLINE";

        success = 'Account created! Entering Chat...';
        
        // This force-reloads to the chat view
        setTimeout(() => {
          window.location.hash = '#/chat';
          window.location.reload(); 
        }, 1000);
      } else {
        error = data.detail || 'Registration failed';
      }
    } catch (err) {
      error = 'Could not reach registration server.';
    } finally {
      loading = false;
    }
  }
  
  function handleResendCode() {
    verificationCode = '';
    handleSendCode();
  }
  
  function handleChangeEmail() {
    step = 1;
    showModal = false;
    if (timerInterval) clearInterval(timerInterval);
  }
</script>