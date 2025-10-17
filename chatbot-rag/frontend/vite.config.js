// vite.config.js
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
      "/health":  { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/reindex": { target: "http://127.0.0.1:8000", changeOrigin: true },

      // Covers /chat and /chat/stream
      "/chat": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        ws: true,          // harmless, but keeps upgrade behavior consistent
        timeout: 0,        // don't time out the client->proxy request
        proxyTimeout: 0,   // don't time out the proxy->backend request
        headers: { Connection: "keep-alive" },
        configure(proxy) {
          proxy.on("error", (err, req, res) => {
            console.error("[vite-proxy] error:", err?.message);
          });
        },
      },
    },
  },
});
