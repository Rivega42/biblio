import React from "react";
import { createRoot } from "react-dom/client";
import "../styles.css";               // design tokens + base (CSS variables)
import "./biblio-bridge.css";         // Biblio Style A skin: maps app aliases → Biblio tokens
import { App } from "./App";

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
