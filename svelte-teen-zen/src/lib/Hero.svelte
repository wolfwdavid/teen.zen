<script>
  let email = '';
  
  function handleSubmit() {
    if (email) {
      alert(`Thanks for subscribing! We'll send updates to ${email}`);
      email = '';
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
      
      <form on:submit|preventDefault={handleSubmit} class="subscribe-form">
        <input 
          type="email" 
          bind:value={email}
          placeholder="Enter your email" 
          required
        />
        <button type="submit">Get Early Access</button>
      </form>
      
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

  .subscribe-form button:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
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
