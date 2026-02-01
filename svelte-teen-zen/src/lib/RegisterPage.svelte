<script>
  import { onMount } from 'svelte';

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

  // --- 1. Health Check Logic ---
  async function checkBackendHealth() {
    try {
      const res = await fetch('http://localhost:8000/health');
      status = res.ok ? "ONLINE" : "OFFLINE";
    } catch (e) {
      status = "OFFLINE";
    }
  }

  onMount(() => {
    checkBackendHealth();
    const healthInterval = setInterval(checkBackendHealth, 30000);
    return () => clearInterval(healthInterval);
  });

  // --- 2. URL Param Handling ---
  if (typeof window !== 'undefined') {
    const hashParts = window.location.hash.split('?');
    if (hashParts.length > 1) {
      const urlParams = new URLSearchParams(hashParts[1]);
      const emailParam = urlParams.get('email');
      if (emailParam) {
        email = decodeURIComponent(emailParam);
        step = 2;
        showModal = true;
        startTimer(300);
      }
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
    return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
  }
  
  // --- 3. API Actions ---
  async function handleSendCode() {
    error = '';
    if (!email) { error = 'Please enter your email'; return; }
    loading = true;
    try {
      const response = await fetch('http://localhost:8000/api/send-verification-code', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email })
      });
      if (response.ok) {
        success = 'Code sent! Check your terminal.';
        step = 2;
        showModal = true;
        startTimer(300);
      } else {
        const data = await response.json();
        error = data.detail || 'Failed to send code';
      }
    } catch (err) {
      error = 'Backend not responding. Is your Python server running?';
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
        body: JSON.stringify({ email, code: verificationCode.trim() })
      });
      if (response.ok) {
        success = 'Email verified!';
        step = 3; 
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
          email,
          password,
          role: accountRole
        })
      });
      
      const data = await response.json();
      
      if (response.ok) {
        // Save auth data
        localStorage.setItem('userEmail', email);
        localStorage.setItem('token', data.access_token);
        localStorage.setItem('isLoggedIn', 'true');

        success = 'Account created! Entering Chat...';
        
        // Redirect to the chat route
        setTimeout(() => {
          window.location.hash = '#/chat';
        }, 1200);
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

<main class="auth-container">
  <div class="status-bar {status.toLowerCase()}">
    Backend: {status}
  </div>

  <div class="auth-card">
    <div class="header-section">
      <h2 class="text-3xl font-bold">Create Account</h2>
      <p class="text-zinc-500">Sign up to sync your document history.</p>
    </div>

    {#if step === 1}
      <form on:submit|preventDefault={handleSendCode}>
        <input type="email" bind:value={email} placeholder="Enter your email" required />
        <button type="submit" disabled={loading}>Send Verification Code</button>
      </form>
    
    {:else if step === 2}
      <form on:submit|preventDefault={handleVerifyCode}>
        <p>A code was sent to {email}</p>
        <input type="text" bind:value={verificationCode} placeholder="Enter Code" required />
        <button type="submit" disabled={loading}>Verify Code</button>
        <button type="button" on:click={handleResendCode}>Resend ({formatTime(timeRemaining)})</button>
      </form>

    {:else if step === 3}
      <form on:submit|preventDefault={handleRegister}>
        <input type="password" bind:value={password} placeholder="Password" required />
        <input type="password" bind:value={confirmPassword} placeholder="Confirm Password" required />
        
        <div class="role-selection">
          <label><input type="radio" bind:group={accountRole} value="user" /> User</label>
          <label><input type="radio" bind:group={accountRole} value="provider" /> Provider</label>
        </div>

        <button type="submit" disabled={loading}>Sign Up Now</button>
      </form>
    {/if}

    {#if error}<p class="error">{error}</p>{/if}
    {#if success}<p class="success">{success}</p>{/if}
  </div>
</main>

<style>
  .auth-container { background: #09090b; color: white; min-height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center; }
  .auth-card { background: #18181b; padding: 2rem; border-radius: 1rem; border: 1px solid #27272a; width: 400px; text-align: center; }
  input { width: 100%; padding: 0.75rem; margin: 0.5rem 0; background: #09090b; border: 1px solid #27272a; color: white; border-radius: 0.5rem; }
  button { width: 100%; padding: 0.75rem; background: #4f46e5; color: white; border: none; border-radius: 0.5rem; cursor: pointer; margin-top: 1rem; }
  .error { color: #ef4444; margin-top: 1rem; }
  .success { color: #10b981; margin-top: 1rem; }
  .status-bar { padding: 0.5rem 1rem; border-radius: 2rem; margin-bottom: 1rem; font-size: 0.8rem; }
  .online { background: rgba(16, 185, 129, 0.2); color: #10b981; }
  .offline { background: rgba(239, 68, 68, 0.2); color: #ef4444; }
</style>