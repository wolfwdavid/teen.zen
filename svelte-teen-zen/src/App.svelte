<script>
  import Hero from './lib/Hero.svelte';
  import Features from './lib/Features.svelte';
  import About from './lib/About.svelte';
  import Impact from './lib/Impact.svelte';
  import CTA from './lib/CTA.svelte';
  import Footer from './lib/Footer.svelte';
  import LoginPage from './lib/LoginPage.svelte';

  // Simple hash-based routing
  let currentPage = 'home';
  
  function handleHashChange() {
    const hash = window.location.hash;
    if (hash === '#/login') {
      currentPage = 'login';
    } else {
      currentPage = 'home';
    }
  }
  
  // Listen for hash changes
  if (typeof window !== 'undefined') {
    window.addEventListener('hashchange', handleHashChange);
    handleHashChange(); // Check initial hash
  }
</script>

{#if currentPage === 'home'}
  <main>
    <Hero />
    <Features />
    <About />
    <Impact />
    <CTA />
    <Footer />
  </main>
{:else if currentPage === 'login'}
  <LoginPage />
{/if}

<style>
  main {
    width: 100%;
    overflow-x: hidden;
  }
</style>