import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Use VITE_BUILD_TARGET=capacitor for native app builds
const isCapacitor = process.env.VITE_BUILD_TARGET === 'capacitor';

export default defineConfig({
  base: isCapacitor ? '/' : '/teen.zen/',
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") }
  },
  server: {
    port: 5173,
    open: true,
  },
});