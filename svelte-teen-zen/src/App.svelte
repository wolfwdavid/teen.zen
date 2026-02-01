<script>
  import Hero from './lib/Hero.svelte';
  import Features from './lib/Features.svelte';
  import About from './lib/About.svelte';
  import Impact from './lib/Impact.svelte';
  import CTA from './lib/CTA.svelte';
  import Footer from './lib/Footer.svelte';
  import LoginPage from './lib/LoginPage.svelte';
  import RegisterPage from './lib/RegisterPage.svelte';
  
 

  let currentPage = 'home';
  
  function handleHashChange() {
    const hash = window.location.hash;
    console.log("Current Hash:", hash); // Add this to debug in your browser console

    if (hash.includes('/chat')) {
      currentPage = 'chat';
    } else if (hash.includes('/login')) {
      currentPage = 'login';
    } else if (hash.includes('/register')) {
      currentPage = 'register';
    } else {
      currentPage = 'home';
    }
  }
  
  if (typeof window !== 'undefined') {
    window.addEventListener('hashchange', handleHashChange);
    handleHashChange();
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
{:else if currentPage === 'register'}
  <RegisterPage />
{:else if currentPage === 'chat'}
  <ChatPage />
{/if}

<style>
  main { width: 100%; overflow-x: hidden; }
</style>