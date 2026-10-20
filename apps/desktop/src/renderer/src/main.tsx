import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App.tsx";
// CSS is intentionally imported for its stylesheet side effect.
// oxlint-disable-next-line import/no-unassigned-import
import "./style.css";

const rootElement = document.querySelector("#root");
if (rootElement === null) {
  throw new Error("Missing root element");
}

createRoot(rootElement).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
