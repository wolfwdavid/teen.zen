<script>
  let email = '';
  let loading = false;
  let message = '';
  let messageType = ''; // 'success' or 'error'
  
  async function handleSubmit() {
    console.log('handleSubmit called with email:', email);
    
    if (!email) {
      console.log('No email entered');
      return;
    }
    
    loading = true;
    message = '';
    
    try {
      console.log('Sending request to backend...');
      
      const response = await fetch('http://localhost:8000/api/send-verification-code', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email: email })
      });
      
      const data = await response.json();
      console.log('Backend response:', data);
      
      if (response.ok) {
        messageType = 'success';
        message = 'Verification code sent! Redirecting...';
        
        console.log('Success! Redirecting in 2 seconds...');
        
        // Redirect to register page with email pre-filled
        setTimeout(() => {
          const redirectUrl = '#/register?email=' + encodeURIComponent(email);
          console.log('Redirecting to:', redirectUrl);
          window.location.hash = redirectUrl;
        }, 2000);
      } else {
        messageType = 'error';
        message = data.detail || 'Failed to send verification code';
        console.error('Backend error:', data);
      }
    } catch (err) {
      messageType = 'error';
      message = 'Network error. Please make sure the backend is running.';
      console.error('Network error:', err);
    } finally {
      loading = false;
    }
  }
</script>

<section class="hero">
  <div class="container">
    <div class="hero-content">
      <h1>Teen.zen</h1>
      <p class="tagline">Your Mental Health Companion</p>
      <p class="description">
        Empower yourself to manage stress, anxiety, and negative thoughts. 
        Join thousands of teens taking control of their mental well-being.
      </p>
      
      {#if message}
        <div class="message" class:success={messageType === 'success'} class:error={messageType === 'error'}>
          {message}
        </div>
      {/if}
      
      <form on:submit|preventDefault={handleSubmit} class="subscribe-form">
        <input 
          type="email" 
          bind:value={email}
          placeholder="Enter your email" 
          required
          disabled={loading}
        />
        <button type="submit" disabled={loading}>
          {loading ? 'Sending...' : 'Get Early Access'}
        </button>
      </form>
      
      <p class="login-link">
        Already have an account? <a href="#/login">Log in</a>
      </p>
      
      <p class="small-text">Free • Available on iOS & Android • Coming Soon</p>
    </div>
    
    <div class="hero-image">
      <div class="phone-mockup">
        <div class="screen">
          <div class="app-preview">
            <div class="preview-header">
              <span class="dot"></span>
              <span class="dot"></span>
              <span class="dot"></span>
            </div>
            <div class="preview-content">
              <h3>Daily Check-in</h3>
              <p>How are you feeling today?</p>
              <div class="mood-buttons">
                <span class="mood">😊</span>
                <span class="mood">😐</span>
                <span class="mood">😔</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</section>

<style>
  .hero {
    min-height: 100vh;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    display: flex;
    align-items: center;
    padding: 4rem 2rem;
    position: relative;
    overflow: hidden;
  }

  .hero::before {
    content: '';
    position: absolute;
    width: 500px;
    height: 500px;
    background: rgba(255, 255, 255, 0.1);
    border-radius: 50%;
    top: -250px;
    right: -250px;
  }

  .container {
    max-width: 1200px;
    margin: 0 auto;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 4rem;
    align-items: center;
    position: relative;
    z-index: 1;
  }

  .hero-content h1 {
    font-size: 4rem;
    font-weight: 800;
    margin-bottom: 1rem;
    letter-spacing: -2px;
  }

  .tagline {
    font-size: 1.5rem;
    margin-bottom: 1.5rem;
    opacity: 0.9;
  }

  .description {
    font-size: 1.1rem;
    margin-bottom: 2rem;
    line-height: 1.8;
    opacity: 0.95;
  }

  .message {
    padding: 1rem 1.5rem;
    border-radius: 10px;
    margin-bottom: 1.5rem;
    font-weight: 500;
    animation: slideIn 0.3s ease-out;
  }

  .message.success {
    background: rgba(76, 175, 80, 0.2);
    border: 1px solid rgba(76, 175, 80, 0.5);
  }

  .message.error {
    background: rgba(244, 67, 54, 0.2);
    border: 1px solid rgba(244, 67, 54, 0.5);
  }

  @keyframes slideIn {
    from {
      opacity: 0;
      transform: translateY(-10px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  .subscribe-form {
    display: flex;
    gap: 1rem;
    margin-bottom: 1rem;
    flex-wrap: wrap;
  }

  .subscribe-form input {
    flex: 1;
    min-width: 250px;
    padding: 1rem 1.5rem;
    border: none;
    border-radius: 50px;
    font-size: 1rem;
    outline: none;
  }

  .subscribe-form input:disabled {
    opacity: 0.7;
    cursor: not-allowed;
  }

  .subscribe-form button {
    padding: 1rem 2.5rem;
    background: #ff6b6b;
    color: white;
    border: none;
    border-radius: 50px;
    font-size: 1rem;
    font-weight: 600;
    cursor: pointer;
    transition: transform 0.2s, box-shadow 0.2s;
  }

  .subscribe-form button:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
  }

  .subscribe-form button:disabled {
    opacity: 0.7;
    cursor: not-allowed;
  }

  .login-link {
    margin-bottom: 0.5rem;
    font-size: 0.95rem;
  }

  .login-link a {
    color: white;
    text-decoration: underline;
    font-weight: 600;
    transition: opacity 0.3s;
  }

  .login-link a:hover {
    opacity: 0.8;
  }

  .small-text {
    font-size: 0.9rem;
    opacity: 0.8;
  }

  .phone-mockup {
    width: 300px;
    height: 600px;
    background: #1a1a1a;
    border-radius: 40px;
    padding: 15px;
    box-shadow: 0 30px 60px rgba(0, 0, 0, 0.3);
    margin: 0 auto;
  }

  .screen {
    width: 100%;
    height: 100%;
    background: white;
    border-radius: 30px;
    overflow: hidden;
  }

  .app-preview {
    padding: 2rem;
    color: #333;
  }

  .preview-header {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 2rem;
  }

  .dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: #ddd;
  }

  .preview-content h3 {
    font-size: 1.5rem;
    margin-bottom: 1rem;
    color: #667eea;
  }

  .preview-content p {
    margin-bottom: 1.5rem;
    color: #666;
  }

  .mood-buttons {
    display: flex;
    gap: 1rem;
    justify-content: center;
  }

  .mood {
    font-size: 3rem;
    cursor: pointer;
    transition: transform 0.2s;
  }

  .mood:hover {
    transform: scale(1.2);
  }

  @media (max-width: 968px) {
    .container {
      grid-template-columns: 1fr;
      gap: 3rem;
    }

    .hero-content h1 {
      font-size: 3rem;
    }

    .phone-mockup {
      width: 250px;
      height: 500px;
    }
  }

  @media (max-width: 640px) {
    .hero {
      padding: 2rem 1rem;
    }

    .hero-content h1 {
      font-size: 2.5rem;
    }

    .tagline {
      font-size: 1.2rem;
    }

    .subscribe-form {
      flex-direction: column;
    }

    .subscribe-form input,
    .subscribe-form button {
      width: 100%;
    }
  }
</style>