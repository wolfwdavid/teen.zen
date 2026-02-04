<script>
  let email = '';
  
  function handleSubmit() {
    if (email) {
      alert(`Thanks! We'll notify you at ${email} when Teen Zen launches.`);
      email = '';
    }
  }
</script>

<section class="cta">
  <div class="container">
    <div class="cta-content">
      <h2>Ready to Start Your Journey?</h2>
      <p>Join the waitlist and be the first to know when Teen Zen launches.</p>
      
      <form on:submit|preventDefault={handleSubmit} class="cta-form">
        <input 
          type="email" 
          bind:value={email}
          placeholder="Enter your email/Phone number" 
          required
        />
        <button type="submit">Join Waitlist</button>
      </form>
      
      <div class="social-proof">
        <div class="proof-item">
          <span class="icon">👥</span>
          <span>5,000+ on waitlist</span>
        </div>
        <div class="proof-item">
          <span class="icon">⭐</span>
          <span>Endorsed by mental health professionals</span>
        </div>
        <div class="proof-item">
          <span class="icon">🎓</span>
          <span>Supported by research institutions</span>
        </div>
      </div>
    </div>
  </div>
</section>

<style>
  .cta {
    padding: 6rem 2rem;
    background: #f8f9fa;
  }

  .container {
    max-width: 800px;
    margin: 0 auto;
  }

  .cta-content {
    text-align: center;
  }

  .cta-content h2 {
    font-size: 2.5rem;
    font-weight: 700;
    color: #333;
    margin-bottom: 1rem;
  }

  .cta-content > p {
    font-size: 1.2rem;
    color: #666;
    margin-bottom: 2.5rem;
  }

  .cta-form {
    display: flex;
    gap: 1rem;
    max-width: 500px;
    margin: 0 auto 3rem;
    flex-wrap: wrap;
    justify-content: center;
  }

  .cta-form input {
    flex: 1;
    min-width: 250px;
    padding: 1rem 1.5rem;
    border: 2px solid #e0e0e0;
    border-radius: 50px;
    font-size: 1rem;
    outline: none;
    transition: border-color 0.3s;
  }

  .cta-form input:focus {
    border-color: #667eea;
  }

  .cta-form button {
    padding: 1rem 2.5rem;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border: none;
    border-radius: 50px;
    font-size: 1rem;
    font-weight: 600;
    cursor: pointer;
    transition: transform 0.2s, box-shadow 0.2s;
  }

  .cta-form button:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
  }

  .social-proof {
    display: flex;
    flex-wrap: wrap;
    gap: 2rem;
    justify-content: center;
    align-items: center;
  }

  .proof-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    color: #666;
    font-size: 0.95rem;
  }

  .icon {
    font-size: 1.5rem;
  }

  @media (max-width: 640px) {
    .cta {
      padding: 4rem 1rem;
    }

    .cta-content h2 {
      font-size: 2rem;
    }

    .cta-form {
      flex-direction: column;
    }

    .cta-form input,
    .cta-form button {
      width: 100%;
    }

    .social-proof {
      flex-direction: column;
      gap: 1rem;
    }
  }
</style>
