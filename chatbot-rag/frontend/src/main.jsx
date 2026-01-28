import React from "react";
import ReactDOM from "react-dom/client";

// ✅ Explicit extension avoids any Vite / path confusion
import App from "./App.jsx";

// ✅ Global styles
import "./styles/theme.css";

const rootEl = document.getElementById("root");

if (!rootEl) {
  throw new Error("Root element #root not found");
}

ReactDOM.createRoot(rootEl).render(
  // 🔥 Temporarily REMOVE StrictMode while debugging SSE / effects
  // StrictMode double-invokes effects in dev and can break streams
  <App />
);
