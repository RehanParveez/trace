import React from "react";
import ReactDOM from "react-dom/client";
import "./styles/index.css";
import "./i18n";
import App from "./App";
import { AppProviders } from "./app/providers";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <AppProviders>
      <App />
    </AppProviders>
  </React.StrictMode>,
);