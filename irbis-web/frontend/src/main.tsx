import React from "react";
import { createRoot } from "react-dom/client";
import "../styles.css";               // design tokens + base (CSS variables)
import "./biblio-bridge.css";         // Biblio Style A skin: maps app aliases → Biblio tokens
import { App } from "./App";
import { Landing } from "./landing/Landing";

// Публичная страница продукта (/product, issue #226) — SPA отдаётся бэкендом на
// /product и подпутях (server.py / app_aiohttp.py), а здесь по pathname выбираем,
// что монтировать: лендинг продукта или читательский портал. Лендинг публичен
// (без логина) и самодостаточен.
const isProduct = window.location.pathname.replace(/\/+$/, "") === "/product";

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    {isProduct ? <Landing /> : <App />}
  </React.StrictMode>,
);
