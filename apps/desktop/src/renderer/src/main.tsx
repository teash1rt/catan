import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App.tsx";
// oxlint-disable-next-line import/no-unassigned-import -- 通过副作用导入加载 CSS 样式。
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
