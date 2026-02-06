import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import "./index.css";

const init = () => {
  const rootEl = document.getElementById("root");
  
  if (rootEl) {
    createRoot(rootEl).render(
      <React.StrictMode>
        <App />
      </React.StrictMode>
    );
    console.log("[frontend] mounted successfully");
  } else {
    // Log a more helpful error for debugging on GitHub Pages
    console.error("Critical Error: #root element not found in the DOM.");
  }
};

// Ensures the DOM is fully loaded before trying to find #root
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}