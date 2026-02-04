<section class="about">
  <div class="container">
    <div class="about-content">
      <h2>Why Teen Zen?</h2>
      <p class="lead">
        Mental health challenges affect a significant percentage of adolescents. 
        Early intervention is critical for improving outcomes.
      </p>
      
      <div class="about-points">
        <div class="point">
          <div class="point-icon">📱</div>
          <div class="point-content">
            <h3>Always Accessible</h3>
            <p>
              Support available 24/7 in your pocket. Get help when and where you need it, 
              especially in underserved communities with limited mental health resources.
            </p>
          </div>
        </div>
        
        <div class="point">
          <div class="point-icon">🤝</div>
          <div class="point-content">
            <h3>Connect with Peers</h3>
            <p>
              Anonymous forums and peer-matching features promote social interaction. 
              Share challenges, offer advice, and connect with others who understand.
            </p>
          </div>
        </div>
        
        <div class="point">
          <div class="point-icon">🔒</div>
          <div class="point-content">
            <h3>Private & Secure</h3>
            <p>
              Your data is protected with the highest privacy standards. 
              Feel safe sharing your thoughts and tracking your progress.
            </p>
          </div>
        </div>
        
        <div class="point">
          <div class="point-icon">🌍</div>
          <div class="point-content">
            <h3>For Everyone</h3>
            <p>
              Completely free and designed to be accessible for all teenagers, 
              regardless of background or location.
            </p>
          </div>
        </div>
      </div>
    </div>
  </div>
</section>

<style>
  .about {
    padding: 6rem 2rem;
    background: white;
  }

  .container {
    max-width: 1000px;
    margin: 0 auto;
  }

  .about-content h2 {
    font-size: 2.5rem;
    font-weight: 700;
    color: #333;
    margin-bottom: 1.5rem;
    text-align: center;
  }

  .lead {
    font-size: 1.3rem;
    color: #666;
    text-align: center;
    margin-bottom: 4rem;
    line-height: 1.8;
  }

  .about-points {
    display: grid;
    gap: 3rem;
  }

  .point {
    display: flex;
    gap: 2rem;
    align-items: start;
  }

  .point-icon {
    font-size: 3rem;
    flex-shrink: 0;
  }

  .point-content h3 {
    font-size: 1.5rem;
    color: #667eea;
    margin-bottom: 0.5rem;
    font-weight: 600;
  }

  .point-content p {
    color: #666;
    line-height: 1.8;
    font-size: 1.05rem;
  }

  @media (max-width: 640px) {
    .about {
      padding: 4rem 1rem;
    }

    .about-content h2 {
      font-size: 2rem;
    }

    .lead {
      font-size: 1.1rem;
    }

    .point {
      flex-direction: column;
      gap: 1rem;
      text-align: center;
    }

    .point-icon {
      margin: 0 auto;
    }
  }
</style>
