<script>
  const currentYear = new Date().getFullYear();
</script>

<footer class="footer">
  <div class="container">
    <div class="footer-content">
      <div class="footer-section">
        <h3>Teen.zen</h3>
        <p>Empowering teenagers to take control of their mental well-being.</p>
        <div class="social-links">
          <a href="#" aria-label="Twitter">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
              <path d="M23 3a10.9 10.9 0 01-3.14 1.53 4.48 4.48 0 00-7.86 3v1A10.66 10.66 0 013 4s-4 9 5 13a11.64 11.64 0 01-7 2c9 5 20 0 20-11.5a4.5 4.5 0 00-.08-.83A7.72 7.72 0 0023 3z"/>
            </svg>
          </a>
          <a href="#" aria-label="Instagram">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="2" y="2" width="20" height="20" rx="5" ry="5"/>
              <path d="M16 11.37A4 4 0 1112.63 8 4 4 0 0116 11.37z"/>
              <line x1="17.5" y1="6.5" x2="17.51" y2="6.5"/>
            </svg>
          </a>
          <a href="#" aria-label="Facebook">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
              <path d="M18 2h-3a5 5 0 00-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 011-1h3z"/>
            </svg>
          </a>
        </div>
      </div>
      
      <div class="footer-section">
        <h4>Product</h4>
        <ul>
          <li><a href="#features">Features</a></li>
          <li><a href="#about">About</a></li>
          <li><a href="#pricing">Pricing</a></li>
          <li><a href="#download">Download</a></li>
        </ul>
      </div>
      
      <div class="footer-section">
        <h4>Resources</h4>
        <ul>
          <li><a href="#blog">Blog</a></li>
          <li><a href="#support">Support</a></li>
          <li><a href="#faq">FAQ</a></li>
          <li><a href="#community">Community</a></li>
        </ul>
      </div>
      
      <div class="footer-section">
        <h4>Legal</h4>
        <ul>
          <li><a href="#privacy">Privacy Policy</a></li>
          <li><a href="#terms">Terms of Service</a></li>
          <li><a href="#cookies">Cookie Policy</a></li>
        </ul>
      </div>
    </div>
    
    <div class="footer-bottom">
      <p>&copy; {currentYear} Teen.zen. All rights reserved.</p>
      <p class="disclaimer">
        This app is not a substitute for professional mental health care. 
        If you're in crisis, please contact a mental health professional or call 988.
      </p>
    </div>
  </div>
</footer>

<style>
  .footer {
    background: #1a1a1a;
    color: white;
    padding: 4rem 2rem 2rem;
  }

  .container {
    max-width: 1200px;
    margin: 0 auto;
  }

  .footer-content {
    display: grid;
    grid-template-columns: 2fr 1fr 1fr 1fr;
    gap: 3rem;
    margin-bottom: 3rem;
  }

  .footer-section h3 {
    font-size: 1.5rem;
    margin-bottom: 1rem;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  .footer-section h4 {
    font-size: 1.1rem;
    margin-bottom: 1rem;
    font-weight: 600;
  }

  .footer-section p {
    color: #999;
    line-height: 1.8;
    margin-bottom: 1.5rem;
  }

  .social-links {
    display: flex;
    gap: 1rem;
  }

  .social-links a {
    width: 40px;
    height: 40px;
    background: rgba(255, 255, 255, 0.1);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    transition: background 0.3s, transform 0.3s;
  }

  .social-links a:hover {
    background: rgba(255, 255, 255, 0.2);
    transform: translateY(-3px);
  }

  .footer-section ul {
    list-style: none;
  }

  .footer-section ul li {
    margin-bottom: 0.75rem;
  }

  .footer-section ul li a {
    color: #999;
    text-decoration: none;
    transition: color 0.3s;
  }

  .footer-section ul li a:hover {
    color: white;
  }

  .footer-bottom {
    border-top: 1px solid rgba(255, 255, 255, 0.1);
    padding-top: 2rem;
    text-align: center;
  }

  .footer-bottom p {
    color: #666;
    margin-bottom: 0.5rem;
  }

  .disclaimer {
    font-size: 0.9rem;
    font-style: italic;
  }

  @media (max-width: 968px) {
    .footer-content {
      grid-template-columns: 1fr 1fr;
      gap: 2rem;
    }
  }

  @media (max-width: 640px) {
    .footer {
      padding: 3rem 1rem 1.5rem;
    }

    .footer-content {
      grid-template-columns: 1fr;
      gap: 2rem;
    }
  }
</style>
