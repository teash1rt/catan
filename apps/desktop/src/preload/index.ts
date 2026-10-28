import { contextBridge, ipcRenderer } from "electron";
import { GOOGLE_SIGN_IN_CHANNEL, googleSignInResultSchema } from "@catan/protocol";
import type { DesktopApi } from "@catan/protocol";

const api: DesktopApi = {
  signInWithGoogle: async () => {
    const result: unknown = await ipcRenderer.invoke(GOOGLE_SIGN_IN_CHANNEL);
    return googleSignInResultSchema.parse(result);
  },
};

contextBridge.exposeInMainWorld("catan", Object.freeze(api));
