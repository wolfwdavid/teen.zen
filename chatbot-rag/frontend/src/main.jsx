import React from "react";
import { createRoot } from "react-dom/client";

import App from "./App.jsx";

// Tailwind v4 entry (contains: @import "tailwindcss";)
import "./index.css";

const rootEl = document.getElementById("root");
if (!rootEl) throw new Error("Root element #root not found");

createRoot(rootEl).render(<App />);

// Optional: quick sanity check in console
console.log("[frontend] mounted");
