<script>
  import Hero from './lib/Hero.svelte';
  import Features from './lib/Features.svelte';
  import About from './lib/About.svelte';
  import Impact from './lib/Impact.svelte';
  import CTA from './lib/CTA.svelte';
  import Footer from './lib/Footer.svelte';
</script>

<main>
  <Hero />
  <Features />
  <About />
  <Impact />
  <CTA />
  <Footer />
</main>

<style>
  main {
    width: 100%;
    overflow-x: hidden;
  }
</style>