import { defineConfig, externalizeDepsPlugin } from "electron-vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ command }) => ({
  main: {
    plugins: [externalizeDepsPlugin()],
  },
  preload: {
    plugins: [externalizeDepsPlugin()],
    build: { rollupOptions: { output: { format: "cjs", entryFileNames: "index.cjs" } } },
  },
  renderer: {
    plugins: [react(), {
      name: "local-renderer-csp",
      transformIndexHtml() {
        return [{ tag: "meta", attrs: { "http-equiv": "Content-Security-Policy",
          content: `default-src 'self'; script-src 'self'${command === "serve" ? " 'unsafe-inline'" : ""}; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self' data: blob:${command === "serve" ? " ws://localhost:*" : ""}; object-src 'none'; base-uri 'self'`,
        }, injectTo: "head-prepend" }];
      },
    }],
  },
}));
