import { app, BrowserWindow, ipcMain, shell } from "electron";
import {
  GOOGLE_SIGN_IN_CHANNEL,
  googleSignInRequestSchema,
  googleSignInResultSchema,
} from "@catan/protocol";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { GoogleLoginError, signInWithGoogle } from "./google-login.ts";

const currentDirectory = dirname(fileURLToPath(import.meta.url));

function createWindow(): void {
  const window = new BrowserWindow({
    width: 1440,
    height: 1000,
    minWidth: 960,
    minHeight: 680,
    backgroundColor: "#102c35",
    title: "Catan · 岛屿工坊",
    webPreferences: {
      preload: join(currentDirectory, "../preload/index.cjs"),
      sandbox: true,
    },
  });

  const rendererUrl = process.env.ELECTRON_RENDERER_URL;
  if (rendererUrl === undefined) {
    void window.loadFile(join(currentDirectory, "../renderer/index.html"));
    return;
  }

  void window.loadURL(rendererUrl);
}

void app.whenReady().then(() => {
  const pendingLogins = new Map<number, AbortController>();
  ipcMain.handle(GOOGLE_SIGN_IN_CHANNEL, async (event, ...args: unknown[]) => {
    const window = BrowserWindow.fromWebContents(event.sender);
    const senderId = event.sender.id;
    if (
      !googleSignInRequestSchema.safeParse(args).success ||
      event.senderFrame !== event.sender.mainFrame ||
      window === null
    ) {
      return googleSignInResultSchema.parse({ ok: false, message: "无效的登录请求。" });
    }

    if (pendingLogins.has(senderId)) {
      return googleSignInResultSchema.parse({ ok: false, message: "请先完成当前 Google 登录。" });
    }

    const controller = new AbortController();
    const cancel = (): void => controller.abort();
    pendingLogins.set(senderId, controller);
    window.once("closed", cancel);
    try {
      const googleId = await signInWithGoogle(
        {
          clientId: import.meta.env.MAIN_VITE_GOOGLE_CLIENT_ID ?? "",
          clientSecret: import.meta.env.MAIN_VITE_GOOGLE_CLIENT_SECRET ?? "",
        },
        (url) => shell.openExternal(url),
        controller.signal,
      );
      if (!window.isDestroyed()) {
        window.show();
        window.focus();
      }

      return googleSignInResultSchema.parse({ ok: true, googleId });
    } catch (error) {
      // 不把 SDK 异常直接发到渲染进程，避免异常携带授权码或客户端凭据。
      return googleSignInResultSchema.parse({
        ok: false,
        message:
          error instanceof GoogleLoginError
            ? error.message
            : "Google 登录未完成，请检查网络及客户端配置后重试。",
      });
    } finally {
      pendingLogins.delete(senderId);
      window.removeListener("closed", cancel);
    }
  });

  app.on("before-quit", () => {
    for (const controller of pendingLogins.values()) {
      controller.abort();
    }
  });

  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});
