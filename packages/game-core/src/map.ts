import { mapConfigSchema } from "@catan/protocol";
import type { MapConfig, Terrain, HarborKind } from "@catan/protocol";

export type Cell = { id: string; q: number; r: number };
export type Vertex = { id: string; u: number; v: number; tileIds: string[] };
export type Edge = { id: string; a: string; b: string; tileIds: string[] };
export type Topology = { vertices: Vertex[]; edges: Edge[]; coast: Edge[] };
const OFFSETS = [
  [2, 0],
  [1, 1],
  [-1, 1],
  [-2, 0],
  [-1, -1],
  [1, -1],
] as const;

// 使用整数格点标识拓扑，避免模型缩放和浮点变换影响共享边与顶点的身份。
export function buildTopology(cells: readonly Cell[]): Topology {
  const vertices = new Map<string, Vertex>();
  const edges = new Map<string, Edge>();
  const ids = new Set<string>();
  const positions = new Set<string>();
  for (const cell of cells) {
    const position = `${cell.q},${cell.r}`;
    if (
      !Number.isSafeInteger(cell.q) ||
      !Number.isSafeInteger(cell.r) ||
      ids.has(cell.id) ||
      positions.has(position)
    ) {
      throw new Error("地图包含重复或无效地块坐标");
    }
    ids.add(cell.id);
    positions.add(position);
    const keys = OFFSETS.map(([x, y]) => {
      const u = 3 * cell.q + x;
      const v = 2 * cell.r + cell.q + y;
      const id = `${u},${v}`;
      const vertex = vertices.get(id) ?? { id, u, v, tileIds: [] };
      vertex.tileIds.push(cell.id);
      vertices.set(id, vertex);
      return id;
    });
    for (let i = 0; i < 6; i++) {
      // 在 Blender XY 坐标中按顺时针定向：陆地在右侧，海洋在左侧。
      const a = keys[(i + 1) % 6]!;
      const b = keys[i]!;
      const id = [a, b].toSorted().join("|");
      const edge = edges.get(id) ?? { id, a, b, tileIds: [] };
      edge.tileIds.push(cell.id);
      edges.set(id, edge);
    }
  }
  const coast = [...edges.values()].filter((edge) => edge.tileIds.length === 1);
  return { vertices: [...vertices.values()], edges: [...edges.values()], coast };
}

export const CLASSIC_RULES = {
  terrainCounts: { forest: 4, brick: 3, stone: 3, wheat: 4, sheep: 4, desert: 1 },
  numbers: [2, 3, 3, 4, 4, 5, 5, 6, 6, 8, 8, 9, 9, 10, 10, 11, 11, 12],
  separateRedNumbers: true,
  harborOffsets: [0, 3, 6, 10, 13, 16, 20, 23, 26],
  harborKinds: [
    "generic",
    "wool",
    "generic",
    "ore",
    "generic",
    "grain",
    "brick",
    "generic",
    "lumber",
  ],
} as const;

export function classicCells(): Cell[] {
  const cells: Cell[] = [];
  for (let q = -2; q <= 2; q++)
    for (let r = -2; r <= 2; r++) {
      if (Math.abs(q + r) <= 2) cells.push({ id: `${q},${r}`, q, r });
    }
  return cells;
}

export function orderedCoast(topology: Topology): Edge[] {
  const start = topology.coast.toSorted((a, b) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0))[0];
  if (!start) return [];
  const outgoing = new Map(topology.coast.map((edge) => [edge.a, edge]));
  const result: Edge[] = [];
  let edge: Edge | undefined = start;
  while (edge && !result.includes(edge)) {
    result.push(edge);
    edge = outgoing.get(edge.b);
  }
  if (edge !== start || result.length !== topology.coast.length)
    throw new Error("经典地图必须只有一条闭合海岸");
  return result;
}

function randomSource(seed: number): () => number {
  let state = seed >>> 0;
  return () => {
    state = (state + 0x6d2b79f5) >>> 0;
    let value = Math.imul(state ^ (state >>> 15), state | 1);
    value ^= value + Math.imul(value ^ (value >>> 7), value | 61);
    return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
  };
}
function shuffle<T>(values: readonly T[], random: () => number): T[] {
  const copy = [...values];
  for (let i = copy.length - 1; i > 0; i--) {
    const j = Math.floor(random() * (i + 1));
    [copy[i], copy[j]] = [copy[j]!, copy[i]!];
  }
  return copy;
}
const red = (number: number | null | undefined): boolean => number === 6 || number === 8;

/** 仅用于本地预览；后续联机地图由服务端房间权威生成。 */
export function createClassicMap(seed: number): MapConfig {
  const random = randomSource(seed);
  const cells = classicCells();
  const topology = buildTopology(cells);
  const terrainKinds: Terrain[] = ["forest", "brick", "stone", "wheat", "sheep", "desert"];
  const terrains = shuffle(
    terrainKinds.flatMap((terrain) =>
      Array<Terrain>(CLASSIC_RULES.terrainCounts[terrain]).fill(terrain),
    ),
    random,
  );
  const tiles = cells.map((cell, index) => ({
    id: cell.id,
    q: cell.q,
    r: cell.r,
    terrain: terrains[index]!,
    number: null as number | null,
  }));
  const producing = tiles.filter((tile) => tile.terrain !== "desert");
  // 限制随机搜索次数，避免特定种子导致界面长时间阻塞。
  let found = false;
  for (let attempt = 0; attempt < 10000; attempt++) {
    const numbers = shuffle(CLASSIC_RULES.numbers, random);
    producing.forEach((tile, index) => {
      tile.number = numbers[index]!;
    });
    const byId = new Map(tiles.map((tile) => [tile.id, tile]));
    if (
      !CLASSIC_RULES.separateRedNumbers ||
      !topology.edges.some(
        (edge) =>
          edge.tileIds.length === 2 && edge.tileIds.every((id) => red(byId.get(id)?.number)),
      )
    ) {
      found = true;
      break;
    }
  }
  if (!found) throw new Error("未能生成有效数字布局，请重试");
  const coast = orderedCoast(topology);
  return validateMapConfig({
    seed,
    tiles,
    harbors: CLASSIC_RULES.harborOffsets.map((offset, i) => ({
      edgeId: coast[offset]!.id,
      kind: CLASSIC_RULES.harborKinds[i],
    })),
    robberTileId: tiles.find((tile) => tile.terrain === "desert")!.id,
  });
}

export function validateMapConfig(input: unknown): MapConfig {
  const config = mapConfigSchema.parse(input);
  const topology = buildTopology(config.tiles);
  if (!config.tiles.some((tile) => tile.id === config.robberTileId))
    throw new Error("强盗引用了不存在的地块");
  if (config.tiles.some((tile) => (tile.terrain === "desert") !== (tile.number === null)))
    throw new Error("沙漠必须无数字，资源地块必须有数字");
  const occupied = new Set<string>();
  const vertices = new Set<string>();
  for (const port of config.harbors) {
    const edge = topology.coast.find((candidate) => candidate.id === port.edgeId);
    if (!edge || occupied.has(edge.id) || vertices.has(edge.a) || vertices.has(edge.b))
      throw new Error("港口位置重复、相邻或不在海岸");
    occupied.add(edge.id);
    vertices.add(edge.a);
    vertices.add(edge.b);
  }
  return config;
}

export function harborRatio(kind: HarborKind): number {
  return kind === "generic" ? 3 : 2;
}
