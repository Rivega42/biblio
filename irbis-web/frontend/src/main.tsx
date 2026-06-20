import React from "react";
import { createRoot } from "react-dom/client";
import "../styles.css";               // design tokens + base (CSS variables)
import { App } from "./App";

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
