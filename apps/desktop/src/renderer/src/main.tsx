import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

const rootElement = document.querySelector("#root");
if (rootElement === null) {
  throw new Error("Missing root element");
}

createRoot(rootElement).render(<StrictMode />);
