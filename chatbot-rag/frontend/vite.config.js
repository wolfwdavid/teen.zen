import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": path.resolve(__dirname, "./src") } },
  server: {
    host: true,          // ✅ IMPORTANT (exposes dev server to emulator)
    port: 5173,
    strictPort: true,
    open: true,
  },
});
