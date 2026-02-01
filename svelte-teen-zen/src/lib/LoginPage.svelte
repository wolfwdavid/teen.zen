<script>
  let email = '';
  let password = '';
  let accountRole = 'user';
  let error = '';
  let loading = false;
  
  function handleLogin() {
    if (!email || !password) {
      error = 'Please enter both email and password';
      return;
    }
    
    // Clear any previous errors
    error = '';
    loading = true;
    
    // Redirect to chatbot registration with email and role pre-filled
    const params = new URLSearchParams({
      email: email,
      role: accountRole
    });
    
    // Redirect to your RAG Chatbot registration page
    window.location.href = 'http://localhost:5174' + params.toString();
  }
  
  function handleGoogleLogin() {
    // Redirect to chatbot for Google authentication
    window.location.href = 'http://localhost:5174/register';
  }
  
  function handleSignup() {
    // Redirect to chatbot registration
    window.location.href = 'http://localhost:5174/register';
  }
</script>

<section class="login-section">
  <div class="container">
    <div class="login-card">
      <div class="login-header">
        <a href="#/" class="back-link">← Back to home</a>
        <h1>Welcome Back</h1>
        <p>Log in to access your Teen.zen chatbot</p>
      </div>
      
      {#if error}
        <div class="error-message">
          {error}
        </div>
      {/if}
      
      <form on:submit|preventDefault={handleLogin} class="login-form">
        <div class="form-group">
          <label for="email">Email</label>
          <input 
            type="email" 
            id="email"
            bind:value={email}
            placeholder="your@email.com" 
            required
            disabled={loading}
          />
        </div>
        
        <div class="form-group">
          <label for="password">Password</label>
          <input 
            type="password" 
            id="password"
            bind:value={password}
            placeholder="Enter your password" 
            required
            disabled={loading}
          />
        </div>
        
        <div class="form-group">
          <label class="section-label">ACCOUNT ROLE</label>
          <div class="role-options-inline">
            <label class="role-checkbox">
              <input 
                type="radio" 
                name="role" 
                value="user"
                bind:group={accountRole}
                disabled={loading}
              />
              <span class="checkbox-custom"></span>
              <span class="role-name">User</span>
            </label>
            
            <label class="role-checkbox">
              <input 
                type="radio" 
                name="role" 
                value="provider"
                bind:group={accountRole}
                disabled={loading}
              />
              <span class="checkbox-custom"></span>
              <span class="role-name">Provider</span>
            </label>
          </div>
        </div>
        
        <div class="form-options">
          <label class="checkbox-label">
            <input type="checkbox" />
            <span>Remember me</span>
          </label>
          <a href="#/forgot-password" class="forgot-link">Forgot password?</a>
        </div>
        
        <button type="submit" class="login-button" disabled={loading}>
          {loading ? 'Redirecting...' : 'Log In to Chatbot'}
        </button>
      </form>
      
      <div class="divider">
        <span>or</span>
      </div>
      
      <div class="social-login">
        <button type="button" class="social-button google" on:click={handleGoogleLogin}>
          <svg width="20" height="20" viewBox="0 0 20 20">
            <path fill="#4285F4" d="M19.6 10.23c0-.82-.1-1.42-.25-2.05H10v3.72h5.5c-.15.96-.74 2.31-2.04 3.22v2.45h3.16c1.89-1.73 2.98-4.3 2.98-7.34z"/>
            <path fill="#34A853" d="M13.46 15.13c-.83.59-1.96 1-3.46 1-2.64 0-4.88-1.74-5.68-4.15H1.07v2.52C2.72 17.75 6.09 20 10 20c2.7 0 4.96-.89 6.62-2.42l-3.16-2.45z"/>
            <path fill="#FBBC05" d="M3.99 10c0-.69.12-1.35.32-1.97V5.51H1.07A9.973 9.973 0 000 10c0 1.61.39 3.14 1.07 4.49l3.24-2.52c-.2-.62-.32-1.28-.32-1.97z"/>
            <path fill="#EA4335" d="M10 3.88c1.88 0 3.13.81 3.85 1.48l2.84-2.76C14.96.99 12.7 0 10 0 6.09 0 2.72 2.25 1.07 5.51l3.24 2.52C5.12 5.62 7.36 3.88 10 3.88z"/>
          </svg>
          Continue with Google
        </button>
      </div>
      
      <p class="signup-prompt">
        Don't have an account? <button type="button" class="signup-link" on:click={handleSignup}>Sign up</button>
      </p>
    </div>
  </div>
</section>

<style>
  .login-section {
    min-height: 100vh;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 2rem;
  }

  .container {
    width: 100%;
    max-width: 450px;
  }

  .login-card {
    background: white;
    border-radius: 20px;
    padding: 3rem;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  }

  .login-header {
    text-align: center;
    margin-bottom: 2rem;
  }

  .back-link {
    display: inline-block;
    color: #667eea;
    text-decoration: none;
    margin-bottom: 1rem;
    font-size: 0.95rem;
  }

  .back-link:hover {
    text-decoration: underline;
  }

  .login-header h1 {
    font-size: 2rem;
    color: #333;
    margin-bottom: 0.5rem;
  }

  .login-header p {
    color: #666;
    font-size: 1rem;
  }

  .error-message {
    background: #fee;
    border: 1px solid #fcc;
    color: #c33;
    padding: 1rem;
    border-radius: 10px;
    margin-bottom: 1.5rem;
    font-size: 0.9rem;
  }

  .login-form {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
  }

  .form-group {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .form-group label {
    font-weight: 600;
    color: #333;
    font-size: 0.95rem;
  }

  .section-label {
    font-weight: 600;
    color: #999;
    font-size: 0.75rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
  }

  .form-group input[type="email"],
  .form-group input[type="password"] {
    padding: 0.875rem 1rem;
    border: 2px solid #e0e0e0;
    border-radius: 10px;
    font-size: 1rem;
    transition: border-color 0.3s;
  }

  .form-group input[type="email"]:focus,
  .form-group input[type="password"]:focus {
    outline: none;
    border-color: #667eea;
  }

  .role-options-inline {
    display: flex;
    gap: 2rem;
    align-items: center;
  }

  .role-checkbox {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    cursor: pointer;
    position: relative;
  }

  .role-checkbox input[type="radio"] {
    position: absolute;
    opacity: 0;
    cursor: pointer;
  }

  .checkbox-custom {
    width: 28px;
    height: 28px;
    border: 2px solid #667eea;
    border-radius: 6px;
    background: transparent;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.3s;
    position: relative;
  }

  .role-checkbox input[type="radio"]:checked + .checkbox-custom {
    background: #667eea;
  }

  .role-checkbox input[type="radio"]:checked + .checkbox-custom::after {
    content: '✓';
    color: white;
    font-size: 18px;
    font-weight: bold;
    position: absolute;
  }

  .role-name {
    font-size: 1.1rem;
    color: #e0e0e0;
    font-weight: 500;
    transition: color 0.3s;
  }

  .role-checkbox input[type="radio"]:checked ~ .role-name {
    color: #333;
  }

  .form-options {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: -0.5rem;
  }

  .checkbox-label {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.9rem;
    color: #666;
    cursor: pointer;
  }

  .checkbox-label input[type="checkbox"] {
    width: 18px;
    height: 18px;
    cursor: pointer;
  }

  .forgot-link {
    color: #667eea;
    text-decoration: none;
    font-size: 0.9rem;
  }

  .forgot-link:hover {
    text-decoration: underline;
  }

  .login-button {
    padding: 1rem;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border: none;
    border-radius: 10px;
    font-size: 1rem;
    font-weight: 600;
    cursor: pointer;
    transition: transform 0.2s, box-shadow 0.2s;
    margin-top: 0.5rem;
  }

  .login-button:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
  }

  .login-button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .divider {
    text-align: center;
    margin: 2rem 0;
    position: relative;
  }

  .divider::before,
  .divider::after {
    content: '';
    position: absolute;
    top: 50%;
    width: 45%;
    height: 1px;
    background: #e0e0e0;
  }

  .divider::before {
    left: 0;
  }

  .divider::after {
    right: 0;
  }

  .divider span {
    background: white;
    padding: 0 1rem;
    color: #999;
    font-size: 0.9rem;
  }

  .social-login {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .social-button {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.75rem;
    padding: 0.875rem;
    border: 2px solid #e0e0e0;
    border-radius: 10px;
    background: white;
    font-size: 1rem;
    font-weight: 500;
    cursor: pointer;
    transition: background 0.3s, border-color 0.3s;
  }

  .social-button:hover {
    background: #f8f8f8;
    border-color: #ccc;
  }

  .signup-prompt {
    text-align: center;
    margin-top: 2rem;
    color: #666;
    font-size: 0.95rem;
  }

  .signup-link {
    background: none;
    border: none;
    color: #667eea;
    text-decoration: none;
    font-weight: 600;
    cursor: pointer;
    font-size: 0.95rem;
    padding: 0;
  }

  .signup-link:hover {
    text-decoration: underline;
  }

  @media (max-width: 640px) {
    .login-card {
      padding: 2rem;
    }

    .login-header h1 {
      font-size: 1.75rem;
    }

    .form-options {
      flex-direction: column;
      align-items: flex-start;
      gap: 0.75rem;
    }
  }
</style>