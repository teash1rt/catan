import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import type { Object3D } from "three";

const files = import.meta.glob<string>("../../../../../../assets/*/model.glb", {
  eager: true,
  query: "?url",
  import: "default",
});
// 主题映射将语义化资产 ID 转为打包 URL，避免依赖磁盘绝对路径或用文件名定义玩法。
export const theme = Object.fromEntries(
  Object.entries(files).map(([path, url]) => [path.split("/").at(-2)!, url]),
);
let pending: Promise<Map<string, Object3D>> | undefined;
export function loadAssets(
  progress: (loaded: number, total: number) => void,
): Promise<Map<string, Object3D>> {
  if (pending) return pending;
  const loader = new GLTFLoader();
  let loaded = 0;
  const entries = Object.entries(theme);
  pending = Promise.all(
    entries.map(async ([id, url]) => {
      const gltf = await loader.loadAsync(url);
      gltf.scene.updateMatrixWorld(true);
      progress(++loaded, entries.length);
      return [id, gltf.scene] as const;
    }),
  )
    .then((results) => new Map(results))
    .catch((error: unknown) => {
      pending = undefined;
      throw error;
    });
  return pending;
}
