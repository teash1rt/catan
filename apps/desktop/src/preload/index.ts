import { contextBridge } from "electron";

contextBridge.exposeInMainWorld("catan", Object.freeze({}));
