<script>
  const stats = [
    { number: '1 in 5', label: 'Teens experience mental health challenges' },
    { number: '50%', label: 'Start by age 14' },
    { number: '75%', label: 'Develop by age 24' },
    { number: '70%', label: 'Don\'t receive adequate treatment' }
  ];
</script>

<section class="impact">
  <div class="container">
    <div class="impact-header">
      <h2>The Mental Health Crisis is Real</h2>
      <p>But together, we can make a difference</p>
    </div>
    
    <div class="stats-grid">
      {#each stats as stat}
        <div class="stat-card">
          <div class="stat-number">{stat.number}</div>
          <div class="stat-label">{stat.label}</div>
        </div>
      {/each}
    </div>
    
    <div class="impact-content">
      <h3>Our Mission</h3>
      <p>
        Teen.zen aims to significantly improve the mental health of teenagers by offering 
        accessible, scientifically-backed tools. We focus on early intervention, promoting 
        awareness, and creating a supportive community while addressing barriers such as 
        stigma, cultural diversity, and accessibility.
      </p>
      
      <div class="impact-features">
        <div class="impact-feature">
          <span class="check">✓</span>
          <span>Evidence-based CBT techniques</span>
        </div>
        <div class="impact-feature">
          <span class="check">✓</span>
          <span>Developed with mental health professionals</span>
        </div>
        <div class="impact-feature">
          <span class="check">✓</span>
          <span>Regular content updates and improvements</span>
        </div>
        <div class="impact-feature">
          <span class="check">✓</span>
          <span>Culturally sensitive and inclusive</span>
        </div>
      </div>
    </div>
  </div>
</section>

<style>
  .impact {
    padding: 6rem 2rem;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
  }

  .container {
    max-width: 1200px;
    margin: 0 auto;
  }

  .impact-header {
    text-align: center;
    margin-bottom: 4rem;
  }

  .impact-header h2 {
    font-size: 2.5rem;
    font-weight: 700;
    margin-bottom: 1rem;
  }

  .impact-header p {
    font-size: 1.2rem;
    opacity: 0.9;
  }

  .stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 2rem;
    margin-bottom: 4rem;
  }

  .stat-card {
    background: rgba(255, 255, 255, 0.1);
    backdrop-filter: blur(10px);
    padding: 2rem;
    border-radius: 20px;
    text-align: center;
    border: 1px solid rgba(255, 255, 255, 0.2);
  }

  .stat-number {
    font-size: 3rem;
    font-weight: 800;
    margin-bottom: 0.5rem;
  }

  .stat-label {
    font-size: 1.1rem;
    opacity: 0.9;
    line-height: 1.4;
  }

  .impact-content {
    max-width: 800px;
    margin: 0 auto;
    text-align: center;
  }

  .impact-content h3 {
    font-size: 2rem;
    margin-bottom: 1.5rem;
    font-weight: 600;
  }

  .impact-content > p {
    font-size: 1.1rem;
    line-height: 1.8;
    margin-bottom: 2rem;
    opacity: 0.95;
  }

  .impact-features {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 1.5rem;
    text-align: left;
  }

  .impact-feature {
    display: flex;
    align-items: center;
    gap: 1rem;
    background: rgba(255, 255, 255, 0.1);
    padding: 1.5rem;
    border-radius: 15px;
    backdrop-filter: blur(10px);
  }

  .check {
    font-size: 1.5rem;
    flex-shrink: 0;
  }

  @media (max-width: 640px) {
    .impact {
      padding: 4rem 1rem;
    }

    .impact-header h2 {
      font-size: 2rem;
    }

    .stats-grid {
      grid-template-columns: repeat(2, 1fr);
      gap: 1rem;
    }

    .stat-number {
      font-size: 2rem;
    }

    .stat-label {
      font-size: 0.9rem;
    }

    .impact-features {
      grid-template-columns: 1fr;
    }
  }
</style>
