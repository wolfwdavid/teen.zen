import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173, // default Vite port, can change if needed
    open: true, // auto-open browser on dev start
    proxy: {
      // Proxy backend API calls to FastAPI
      "/chat": {
        target: "http://localhost:9000",
        changeOrigin: true,
      },
    },
  },
  optimizeDeps: {
    include: ["react", "react-dom"], // ensures deps are pre-bundled
  },
  build: {
    outDir: "dist",
    sourcemap: true,
  },
});
