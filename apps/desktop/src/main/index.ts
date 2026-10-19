import { app, BrowserWindow } from "electron";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

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
