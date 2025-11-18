import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": path.resolve(__dirname, "./src") } },
  server: {
    port: 5173,
    open: true,
    proxy: {
      "/health":      { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/chat":        { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/chat/stream": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/reindex":     { target: "http://127.0.0.1:8000", changeOrigin: true },
    },
  },
});
