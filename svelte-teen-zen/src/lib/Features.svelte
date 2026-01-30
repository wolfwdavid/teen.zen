<script>
  const features = [
    {
      icon: '🧠',
      title: 'Self-Paced Lessons',
      description: 'Expert-designed CBT lessons to help you understand and manage your thoughts, emotions, and behaviors at your own pace.'
    },
    {
      icon: '✅',
      title: 'Daily Tasks',
      description: 'Quick, effective activities that integrate into your routine to build resilience and positive habits.'
    },
    {
      icon: '📔',
      title: 'Mood Journal',
      description: 'Track your emotional patterns, identify triggers, and gain insights into your mental health journey.'
    },
    {
      icon: '🎯',
      title: 'Habit Building',
      description: 'Proven strategies and tips to establish healthy habits and effectively manage daily stress.'
    },
    {
      icon: '📊',
      title: 'Progress Tracking',
      description: 'Weekly assessments to monitor your progress and gain valuable emotional insights.'
    },
    {
      icon: '⚡',
      title: 'Quick Relief',
      description: 'Instant stress management tools for high-pressure moments when you need support most.'
    }
  ];
</script>

<section class="features">
  <div class="container">
    <div class="section-header">
      <h2>Everything You Need for Better Mental Health</h2>
      <p>Scientifically-backed tools designed specifically for teens</p>
    </div>
    
    <div class="features-grid">
      {#each features as feature}
        <div class="feature-card">
          <div class="feature-icon">{feature.icon}</div>
          <h3>{feature.title}</h3>
          <p>{feature.description}</p>
        </div>
      {/each}
    </div>
  </div>
</section>

<style>
  .features {
    padding: 6rem 2rem;
    background: #f8f9fa;
  }

  .container {
    max-width: 1200px;
    margin: 0 auto;
  }

  .section-header {
    text-align: center;
    margin-bottom: 4rem;
  }

  .section-header h2 {
    font-size: 2.5rem;
    font-weight: 700;
    color: #333;
    margin-bottom: 1rem;
  }

  .section-header p {
    font-size: 1.2rem;
    color: #666;
  }

  .features-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 2rem;
  }

  .feature-card {
    background: white;
    padding: 2.5rem;
    border-radius: 20px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
    transition: transform 0.3s, box-shadow 0.3s;
    text-align: center;
  }

  .feature-card:hover {
    transform: translateY(-10px);
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.12);
  }

  .feature-icon {
    font-size: 4rem;
    margin-bottom: 1.5rem;
  }

  .feature-card h3 {
    font-size: 1.5rem;
    color: #667eea;
    margin-bottom: 1rem;
    font-weight: 600;
  }

  .feature-card p {
    color: #666;
    line-height: 1.8;
  }

  @media (max-width: 640px) {
    .features {
      padding: 4rem 1rem;
    }

    .section-header h2 {
      font-size: 2rem;
    }

    .features-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
