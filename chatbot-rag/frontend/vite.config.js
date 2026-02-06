import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";
import { fileURLToPath } from "url";

// Manually define __dirname for ES Modules
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export default defineConfig({
  // Ensure this matches your GitHub repo name exactly
  base: '/teen.zen/', 
  plugins: [react(), tailwindcss()],
  resolve: { 
    alias: { "@": path.resolve(__dirname, "./src") } 
  },
  server: {
    port: 5173,
    open: true,
  },
});