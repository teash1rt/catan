import { CanvasTexture, Group, Mesh, MeshBasicMaterial, PlaneGeometry, SRGBColorSpace } from "three";
import type { MapConfig } from "@catan/protocol";
import { anchor } from "./assembly.ts";
import type { AssetLibrary } from "./assembly.ts";
import { createLayout, TERRAIN_ASSETS } from "./layout.ts";

// Runtime content only: models remain blank, and numbers can be removed independently.
export function createNumbers(assets: AssetLibrary, config: MapConfig, tileGap = 0): Group {
  const group = new Group(); const layout = createLayout(config, false, undefined, 1, tileGap);
  const disposables: { dispose(): void }[] = [];
  const materials = new Map<number, MeshBasicMaterial>();
  const geometry = new PlaneGeometry(.62, .65); geometry.rotateX(-Math.PI / 2); disposables.push(geometry);
  for (const tile of config.tiles) {
    if (tile.number === null) continue;
    let material = materials.get(tile.number);
    if (!material) {
      const canvas = document.createElement("canvas"); canvas.width = 256; canvas.height = 256;
      const ctx = canvas.getContext("2d"); if (!ctx) throw new Error("数字纹理画布不可用");
      ctx.fillStyle = tile.number === 6 || tile.number === 8 ? "#aa362a" : "#30261c";
      ctx.textAlign = "center"; ctx.textBaseline = "middle";
      ctx.font = "bold 158px Georgia, serif"; ctx.fillText(String(tile.number), 128, 105, 244);
      const dots = 6 - Math.abs(7 - tile.number);
      for (let i = 0; i < dots; i++) {
        ctx.beginPath(); ctx.arc(128 + (i - (dots - 1) / 2) * 24, 215, 7, 0, Math.PI * 2); ctx.fill();
      }
      const texture = new CanvasTexture(canvas); texture.colorSpace = SRGBColorSpace;
      material = new MeshBasicMaterial({ map: texture, transparent: true, depthWrite: false, toneMapped: false });
      materials.set(tile.number, material); disposables.push(texture, material);
    }
    const mesh = new Mesh(geometry, material);
    const tileMatrix = layout.tiles.get(tile.id)!;
    mesh.matrixAutoUpdate = false;
    mesh.matrix.copy(tileMatrix).multiply(anchor(assets, TERRAIN_ASSETS[tile.terrain], "anchor_number"))
      .multiply(anchor(assets, "number-token", "anchor_content"));
    group.add(mesh);
  }
  group.userData.dispose = () => disposables.forEach(resource => resource.dispose());
  return group;
}
