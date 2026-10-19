import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import type { Object3D } from "three";

const files = import.meta.glob<string>("../../../../../../assets/*/model.glb", { eager: true, query: "?url", import: "default" });
// Theme seam: semantic asset ID -> bundled URL. No absolute disk paths or filename-based game rules.
export const theme = Object.fromEntries(Object.entries(files).map(([path, url]) => [path.split("/").at(-2)!, url]));
let pending: Promise<Map<string, Object3D>> | undefined;
export function loadAssets(progress: (loaded: number, total: number) => void): Promise<Map<string, Object3D>> {
  if (pending) return pending;
  const loader = new GLTFLoader(); let loaded = 0;
  const entries = Object.entries(theme);
  pending = Promise.all(entries.map(async ([id, url]) => {
    const gltf = await loader.loadAsync(url);
    gltf.scene.updateMatrixWorld(true); progress(++loaded, entries.length);
    return [id, gltf.scene] as const;
  })).then(results => new Map(results)).catch((error: unknown) => { pending = undefined; throw error; });
  return pending;
}
