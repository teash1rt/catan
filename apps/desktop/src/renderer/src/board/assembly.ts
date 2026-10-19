import { CylinderGeometry, Group, InstancedMesh, Mesh, MeshStandardMaterial } from "three";
import type { BufferGeometry, Material, Matrix4, Object3D } from "three";
import type { MapConfig } from "@catan/protocol";
import { createLayout, TERRAIN_ASSETS, tileSpacing } from "./layout.ts";

export type AssetLibrary = ReadonlyMap<string, Object3D>;
export function anchor(assets: AssetLibrary, id: string, name: string): Matrix4 {
  const node = assets.get(id)?.getObjectByName(name);
  if (!node) throw new Error(`资产契约缺失：${id}/${name}`);
  return node.matrixWorld.clone();
}
type Batch = { geometry: BufferGeometry; material: Material | Material[]; matrices: Matrix4[]; sea: boolean };

/** Every repeated GLB node shares GPU geometry; cached original materials remain immutable. */
export function assembleBoard(assets: AssetLibrary, config: MapConfig, pieces: boolean, color: string, buildingScale = 1, tileGap = 0): Group {
  const layout = createLayout(config, pieces, color, buildingScale, tileGap);
  const experimentResources: { dispose(): void }[] = [];
  const batches = new Map<string, Batch>(); const playerMaterials = new Map<string, Material>();
  const group = new Group(); group.name = "assembled-board";
  function materialFor(material: Material, playerColor?: string): Material {
    if (!playerColor || material.name !== "player_color") return material;
    const key = `${material.uuid}/${playerColor}`;
    let copy = playerMaterials.get(key);
    if (!copy) {
      copy = material.clone();
      if (!(copy instanceof MeshStandardMaterial)) throw new Error("玩家材质必须是标准 PBR 材质");
      copy.color.set(playerColor); playerMaterials.set(key, copy);
    }
    return copy;
  }
  function add(id: string, matrix: Matrix4, playerColor?: string): void {
    const scene = assets.get(id); if (!scene) throw new Error(`缺少模型：${id}`);
    scene.traverse(node => {
      if (!(node instanceof Mesh)) return;
      const material = Array.isArray(node.material) ? node.material.map(m => materialFor(m, playerColor)) : materialFor(node.material, playerColor);
      const key = `${node.geometry.uuid}/${(Array.isArray(material) ? material : [material]).map(m => m.uuid).join(",")}`;
      const batch: Batch = batches.get(key) ?? { geometry: node.geometry, material, matrices: [], sea: id === "sea-surface" };
      batch.matrices.push(matrix.clone().multiply(node.matrixWorld)); batches.set(key, batch);
    });
  }
  for (const placement of layout.placements) {
    let matrix = placement.matrix;
    if (placement.asset.startsWith("harbor-marker-")) matrix = matrix.clone().multiply(anchor(assets, "harbor", "anchor_trade"));
    add(placement.asset, matrix, placement.color);
  }
  for (const tile of config.tiles) {
    const matrix = layout.tiles.get(tile.id)!;
    const id = TERRAIN_ASSETS[tile.terrain];
    if (tile.number !== null) add("number-token", matrix.clone().multiply(anchor(assets, id, "anchor_number")));
    if (tile.id === config.robberTileId) add("robber", matrix.clone().multiply(anchor(assets, id, "anchor_robber")));
  }
  for (const [key, batch] of batches) {
    const mesh = new InstancedMesh(batch.geometry, batch.material, batch.matrices.length);
    mesh.name = key;
    batch.matrices.forEach((matrix, i) => mesh.setMatrixAt(i, matrix));
    mesh.instanceMatrix.needsUpdate = true; mesh.computeBoundingSphere();
    mesh.castShadow = !batch.sea; mesh.receiveShadow = true;
    group.add(mesh);
  }
  group.userData.batchCount = batches.size;
  if (tileGap > 0) {
    // Temporary neutral ground under the separated tiles, not a new canonical asset.
    const radius = 3 * tileSpacing(tileGap);
    const geometry = new CylinderGeometry(radius, radius, .295, 6, 1, false, Math.PI / 2);
    geometry.translate(0, -.1525, 0);
    const material = new MeshStandardMaterial({ color: "#c8b17d", roughness: .95 });
    const ground = new InstancedMesh(geometry, material, layout.tiles.size); ground.name = "experiment-gap-ground";
    [...layout.tiles.values()].forEach((matrix, i) => ground.setMatrixAt(i, matrix));
    ground.instanceMatrix.needsUpdate = true; ground.computeBoundingSphere(); ground.receiveShadow = true;
    group.add(ground); experimentResources.push(geometry, material);
  }
  group.userData.dispose = () => {
    group.traverse(node => { if (node instanceof InstancedMesh) node.dispose(); });
    playerMaterials.forEach(material => material.dispose());
    experimentResources.forEach(resource => resource.dispose());
  };
  return group;
}
