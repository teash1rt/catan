import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { InstancedMesh, Matrix4, Mesh, Vector3 } from "three";
import { createClassicMap } from "@catan/game-core";
import { BOARD_PRESENTATION, BUILDING_SCALES, createLayout, transform, TERRAIN_ASSETS, tileSpacing } from "../src/renderer/src/board/layout.ts";
import { anchor, assembleBoard } from "../src/renderer/src/board/assembly.ts";
import { createNumbers } from "../src/renderer/src/board/numbers.ts";

const assets = new Map(); const loader = new GLTFLoader();
const dir = new URL("../../../assets/", import.meta.url);
const assetIds = fs.readdirSync(dir, { withFileTypes: true }).filter(entry => entry.isDirectory()).map(entry => entry.name);
await Promise.all(assetIds.map(async id => {
  assert.deepEqual(fs.readdirSync(new URL(`${id}/`, dir)).toSorted(), ["model.blend", "model.glb"]);
  const bytes = fs.readFileSync(new URL(`${id}/model.glb`, dir));
  const gltf = await loader.parseAsync(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength), "");
  gltf.scene.updateMatrixWorld(true); assets.set(id, gltf.scene);
}));
void test("selected presentation stays x=0.4/y=5 across seeds and piece visibility", () => {
  assert.deepEqual(BOARD_PRESENTATION, { tileGap: .4, buildingScale: 5 });
  assert.ok(Object.isFrozen(BOARD_PRESENTATION));
  for (const seed of [42, 20261019, 2907596087]) for (const pieces of [true, false]) {
    const { buildingScale, tileGap } = BOARD_PRESENTATION;
    const layout = createLayout(createClassicMap(seed), pieces, "#b95843", buildingScale, tileGap);
    const buildings = layout.placements.filter(p => ["settlement", "city"].includes(p.asset));
    assert.equal(buildings.length, pieces ? 2 : 0);
    for (const building of buildings) assert.ok(new Vector3().setFromMatrixScale(building.matrix).equals(new Vector3(5, 5, 5)));
    const centers = [...layout.tiles.values()].map(m => new Vector3().setFromMatrixPosition(m));
    const nearest = Math.min(...centers.flatMap((a, i) => centers.slice(i + 1).map(b => a.distanceTo(b))));
    assert.ok(Math.abs(nearest - (3 * Math.sqrt(3) + .4)) < 1e-9);
  }
});
void test("24 GLBs load; all tile anchors and player material interfaces survive export", () => {
  assert.equal(assets.size, 24);
  for (const id of Object.values(TERRAIN_ASSETS)) {
    const number = new Vector3().setFromMatrixPosition(anchor(assets, id, "anchor_number"));
    assert.ok(number.distanceTo(new Vector3(-.55, 0, .72)) < 1e-5);
    assert.ok(new Vector3().setFromMatrixPosition(anchor(assets, id, "anchor_robber")).distanceTo(new Vector3(.7, 0, .83)) < 1e-5);
  }
  for (const id of ["road", "settlement", "city"]) {
    let hasPlayer = false; assets.get(id).traverse(o => { if (o instanceof Mesh && o.material.name === "player_color") hasPlayer = true; });
    assert.ok(hasPlayer);
  }
  assert.throws(() => anchor(assets, "forest-tile", "missing"));
});
void test("classic assembly produces 9 clear outward ports, continuous joins, no baked board", () => {
  const layout = createLayout(createClassicMap(42));
  assert.equal(layout.coastCount, 30);
  const count = name => layout.placements.filter(p => p.asset === name).length;
  assert.equal(count("map-support-hex"), 19); assert.equal(count("coast-edge"), 21);
  assert.equal(count("coast-edge-harbor"), 9); assert.equal(count("harbor"), 9);
  assert.equal(count("coast-corner-convex"), 18); assert.equal(count("coast-corner-concave"), 12);
  assert.equal(count("sea-surface"), 1);
  const corners = layout.placements.filter(p => p.asset.startsWith("coast-corner"));
  const shores = layout.placements.filter(p => p.asset.startsWith("coast-edge"));
  for (const corner of corners) for (const name of ["anchor_join_in", "anchor_join_out"]) {
    const point = new Vector3().setFromMatrixPosition(corner.matrix.clone().multiply(anchor(assets, corner.asset, name)));
    assert.ok(shores.some(shore => ["anchor_join_a", "anchor_join_b"].some(join =>
      point.distanceTo(new Vector3().setFromMatrixPosition(shore.matrix.clone().multiply(anchor(assets, shore.asset, join)))) < 1e-5)));
  }
  assert.ok(new Vector3(0, 0, -1).applyMatrix4(transform(0, 0, 0, Math.PI / 2)).distanceTo(new Vector3(-1, 0, 0)) < 1e-6);
});
void test("instancing batches repeated details, preserves triangle instances and isolates player color", () => {
  const map = createClassicMap(123);
  const group = assembleBoard(assets, map, true, "#ff0000");
  assert.ok(group.children.every(o => o instanceof InstancedMesh));
  assert.ok(group.children.length < 300, `${group.children.length} batches`);
  assert.ok(group.children.some(o => o.count > 100));
  let colored = false;
  for (const mesh of group.children) {
    if (mesh.material.name === "player_color") { assert.equal(mesh.material.color.getHexString(), "ff0000"); colored = true; }
  }
  assert.ok(colored);
  for (const id of ["road", "settlement", "city"]) assets.get(id).traverse(o => {
    if (o instanceof Mesh && o.material.name === "player_color") assert.notEqual(o.material.color.getHexString(), "ff0000");
  });
  group.userData.dispose();
});

void test("scale experiment changes only building size, not anchors, roads, map or cached models", () => {
  const map = createClassicMap(20261019), serialized = JSON.stringify(map);
  const base = createLayout(map, true);
  const originalMatrices = [...assets.values()].flatMap(scene => {
    const result = []; scene.traverse(node => result.push([node, node.matrixWorld.clone()])); return result;
  });
  for (const scale of BUILDING_SCALES) {
    const layout = createLayout(map, true, "#b95843", scale);
    assert.equal(layout.placements.length, base.placements.length);
    let buildings = 0;
    for (const [i, placement] of layout.placements.entries()) {
      const before = base.placements[i]; assert.equal(placement.asset, before.asset);
      if (["settlement", "city"].includes(placement.asset)) {
        buildings++;
        assert.ok(new Vector3().setFromMatrixPosition(placement.matrix).equals(new Vector3().setFromMatrixPosition(before.matrix)));
        assert.ok(new Vector3().setFromMatrixScale(placement.matrix).distanceTo(new Vector3(scale, scale, scale)) < 1e-9);
      } else assert.ok(placement.matrix.equals(before.matrix));
    }
    assert.equal(buildings, 2);
    const group = assembleBoard(assets, map, true, "#b95843", scale);
    // The renderer applies the scale to every GLB submesh, including player-color roofs.
    for (const id of ["settlement", "city"]) {
      const placement = layout.placements.find(p => p.asset === id);
      assets.get(id).traverse(node => {
        if (!(node instanceof Mesh)) return;
        const batch = group.children.find(mesh => mesh.geometry === node.geometry);
        assert.ok(batch);
        const actual = new Matrix4(); batch.getMatrixAt(0, actual);
        const expected = placement.matrix.clone().multiply(node.matrixWorld);
        assert.ok(actual.elements.every((value, i) => Math.abs(value - expected.elements[i]) < 1e-5));
      });
    }
    group.userData.dispose();
  }
  assert.equal(JSON.stringify(map), serialized);
  for (const [node, matrix] of originalMatrices) assert.ok(node.matrixWorld.equals(matrix));
  assert.throws(() => createLayout(map, true, "#b95843", 0));
  assert.throws(() => createLayout(map, true, "#b95843", NaN));
});

void test("x/y cross experiment keeps terrain size, shared topology and content attachments independent", () => {
  const map = createClassicMap(2907596087), serialized = JSON.stringify(map);
  const base = createLayout(map, true);
  const previousDocument = Object.getOwnPropertyDescriptor(globalThis, "document");
  // Only the text canvas is stubbed; all asset and placement matrices are real.
  Object.defineProperty(globalThis, "document", { configurable: true, value: {
    createElement: () => ({ getContext: () => ({ fillText() {}, beginPath() {}, arc() {}, fill() {} }) }),
  } });
  try {
    for (const gap of [0, .4, 1, 2]) for (const scale of [1, 2.5, 3.7, 5]) {
      const spacing = tileSpacing(gap);
      const layout = createLayout(map, true, "#b95843", scale, gap);
      for (const [id, matrix] of layout.tiles) {
        const expected = new Vector3().setFromMatrixPosition(base.tiles.get(id)).multiplyScalar(spacing);
        assert.ok(new Vector3().setFromMatrixPosition(matrix).distanceTo(expected) < 1e-9);
        assert.ok(new Vector3().setFromMatrixScale(matrix).equals(new Vector3(1, 1, 1)));
      }
      const centers = [...layout.tiles.values()].map(m => new Vector3().setFromMatrixPosition(m));
      const nearest = Math.min(...centers.flatMap((a, i) => centers.slice(i + 1).map(b => a.distanceTo(b))));
      assert.ok(Math.abs(nearest - (3 * Math.sqrt(3) + gap)) < 1e-9);
      for (const [i, placement] of layout.placements.entries()) {
        if (!["settlement", "city", "road"].includes(placement.asset)) continue;
        const expected = new Vector3().setFromMatrixPosition(base.placements[i].matrix).multiplyScalar(spacing);
        assert.ok(new Vector3().setFromMatrixPosition(placement.matrix).distanceTo(expected) < 1e-9);
        const expectedScale = placement.asset === "road" ? new Vector3(spacing, 1, 1) : new Vector3(scale, scale, scale);
        assert.ok(new Vector3().setFromMatrixScale(placement.matrix).distanceTo(expectedScale) < 1e-9);
      }
      const corners = layout.placements.filter(p => p.asset.startsWith("coast-corner"));
      const shores = layout.placements.filter(p => p.asset.startsWith("coast-edge"));
      for (const corner of corners) for (const name of ["anchor_join_in", "anchor_join_out"]) {
        const point = new Vector3().setFromMatrixPosition(corner.matrix.clone().multiply(anchor(assets, corner.asset, name)));
        assert.ok(shores.some(shore => ["anchor_join_a", "anchor_join_b"].some(join =>
          point.distanceTo(new Vector3().setFromMatrixPosition(shore.matrix.clone().multiply(anchor(assets, shore.asset, join)))) < 1e-5)));
      }
      const group = assembleBoard(assets, map, true, "#b95843", scale, gap);
      const ground = group.getObjectByName("experiment-gap-ground");
      assert.equal(Boolean(ground), gap > 0); if (ground) assert.equal(ground.count, 19);
      const numbers = createNumbers(assets, map, gap);
      assert.equal(numbers.children.length, 18);
      for (const [i, tile] of map.tiles.filter(t => t.number !== null).entries()) {
        const expected = layout.tiles.get(tile.id).clone().multiply(anchor(assets, TERRAIN_ASSETS[tile.terrain], "anchor_number"))
          .multiply(anchor(assets, "number-token", "anchor_content"));
        assert.ok(numbers.children[i].matrix.equals(expected));
      }
      const robberTile = map.tiles.find(tile => tile.id === map.robberTileId);
      const robberMatrix = layout.tiles.get(robberTile.id).clone().multiply(anchor(assets, TERRAIN_ASSETS[robberTile.terrain], "anchor_robber"));
      assets.get("robber").traverse(node => {
        if (!(node instanceof Mesh)) return;
        const batch = group.children.find(mesh => mesh.geometry === node.geometry);
        const actual = new Matrix4(); batch.getMatrixAt(0, actual);
        const expected = robberMatrix.clone().multiply(node.matrixWorld);
        assert.ok(actual.elements.every((v, i) => Math.abs(v - expected.elements[i]) < 1e-5));
      });
      numbers.userData.dispose(); group.userData.dispose();
    }
  } finally {
    if (previousDocument) Object.defineProperty(globalThis, "document", previousDocument);
    else delete globalThis.document;
  }
  assert.equal(JSON.stringify(map), serialized);
  for (const gap of [-.1, 2.1, NaN, Infinity]) assert.throws(() => createLayout(map, true, "#b95843", 2.5, gap));
  assert.throws(() => createLayout(map, true, "#b95843", 5.1));
});
