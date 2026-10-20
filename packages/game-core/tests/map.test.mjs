import assert from "node:assert/strict";
import test from "node:test";
import {
  buildTopology,
  classicCells,
  createClassicMap,
  CLASSIC_RULES,
  orderedCoast,
  validateMapConfig,
} from "../dist/index.js";

const sorted = (values) => values.toSorted((a, b) => a - b);
void test("classic topology has 19 cells, 72 unique edges, 54 vertices and 30 coastal edges", () => {
  const topology = buildTopology(classicCells());
  assert.equal(topology.edges.length, 72);
  assert.equal(topology.vertices.length, 54);
  assert.equal(topology.coast.length, 30);
  assert.equal(orderedCoast(topology).length, 30);
  assert.equal(topology.edges.filter((edge) => edge.tileIds.length === 2).length, 42);
});
void test("1000 deterministic seeds preserve resource/number/harbor counts and separate 6/8", () => {
  for (let seed = 0; seed < 1000; seed++) {
    const map = createClassicMap(seed);
    const topology = buildTopology(map.tiles);
    assert.equal(map.tiles.length, 19);
    for (const [terrain, count] of Object.entries(CLASSIC_RULES.terrainCounts))
      assert.equal(map.tiles.filter((tile) => tile.terrain === terrain).length, count);
    assert.deepEqual(
      sorted(map.tiles.flatMap((tile) => (tile.number === null ? [] : [tile.number]))),
      sorted(CLASSIC_RULES.numbers),
    );
    const byId = new Map(map.tiles.map((tile) => [tile.id, tile]));
    assert.equal(byId.get(map.robberTileId).terrain, "desert");
    assert.equal(byId.get(map.robberTileId).number, null);
    for (const edge of topology.edges.filter((candidate) => candidate.tileIds.length === 2))
      assert.ok(!edge.tileIds.every((id) => [6, 8].includes(byId.get(id).number)));
    assert.equal(map.harbors.length, 9);
    assert.equal(map.harbors.filter((p) => p.kind === "generic").length, 4);
    for (const kind of ["lumber", "brick", "ore", "grain", "wool"])
      assert.equal(map.harbors.filter((p) => p.kind === kind).length, 1);
  }
  assert.deepEqual(createClassicMap(42), createClassicMap(42));
  assert.notDeepEqual(createClassicMap(42).tiles, createClassicMap(43).tiles);
  assert.deepEqual(createClassicMap(42).harbors, createClassicMap(43).harbors);
});
void test("boundary rejects malformed, duplicate, invalid number and harbor references", () => {
  const map = createClassicMap(42);
  assert.throws(() => validateMapConfig({ ...map, seed: -1 }));
  assert.throws(() => validateMapConfig({ ...map, robberTileId: "missing" }));
  assert.throws(() => validateMapConfig({ ...map, tiles: [...map.tiles, map.tiles[0]] }));
  assert.throws(() =>
    validateMapConfig({ ...map, tiles: map.tiles.map((t, i) => (i ? t : { ...t, number: 7 })) }),
  );
  assert.throws(() =>
    validateMapConfig({ ...map, harbors: [{ edgeId: "missing", kind: "generic" }] }),
  );
  assert.throws(() => validateMapConfig({ ...map, harbors: [...map.harbors, map.harbors[0]] }));
});
void test("generic topology covers a hole and separated islands without duplicate slots", () => {
  const ring = classicCells().filter(
    (c) => Math.max(Math.abs(c.q), Math.abs(c.r), Math.abs(c.q + c.r)) === 1,
  );
  const topology = buildTopology(ring);
  assert.equal(topology.edges.length, 30);
  assert.equal(topology.coast.length, 24);
  assert.equal(
    buildTopology([
      { id: "a", q: 0, r: 0 },
      { id: "b", q: 5, r: 0 },
    ]).coast.length,
    12,
  );
});
