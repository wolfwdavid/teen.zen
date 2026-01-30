import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [svelte()],
  base: '/teen.zen/', // Change this to your GitHub repo name
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
  }
})
