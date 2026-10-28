import type { DesktopApi } from "@catan/protocol";

declare global {
  interface Window {
    catan: DesktopApi;
  }
}
