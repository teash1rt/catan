import { buildTopology, validateMapConfig } from "@catan/game-core";
import type { MapConfig, Terrain } from "@catan/protocol";
import { Matrix4, Vector3 } from "three";

export const TERRAIN_ASSETS: Record<Terrain, string> = {
  forest: "forest-tile", brick: "brick-tile", stone: "stone-tile",
  wheat: "wheat-tile", sheep: "sheep-tile", desert: "desert-tile",
};
export const BUILDING_SCALES = [1, 1.8, 2.5, 3, 4, 5] as const;
// User-selected presentation; runtime controls must not reset these values.
export const BOARD_PRESENTATION = Object.freeze({ tileGap: .4, buildingScale: 5 });
export const TILE_GAP_RANGE = { min: 0, max: 2, step: .05 } as const;
export const BUILDING_SCALE_RANGE = { min: 1, max: 5, step: .1 } as const;
export function tileSpacing(gap: number): number {
  if (!Number.isFinite(gap) || gap < TILE_GAP_RANGE.min || gap > TILE_GAP_RANGE.max) throw new Error("地块间距超出实验范围");
  return 1 + gap / (3 * Math.sqrt(3));
}
export type Placement = { asset: string; matrix: Matrix4; tileId?: string; color?: string };
export type BoardLayout = { placements: Placement[]; tiles: Map<string, Matrix4>; coastCount: number };
// Layout math uses Blender XY; this one boundary converts to the already Y-up GLBs.
export function transform(x: number, y: number, height = 0, angle = 0): Matrix4 {
  return new Matrix4().makeTranslation(x, height, -y).multiply(new Matrix4().makeRotationY(angle));
}

export function createLayout(input: MapConfig, showPieces = false, color = "#b95843", buildingScale = 1, tileGap = 0): BoardLayout {
  if (!Number.isFinite(buildingScale) || buildingScale < BUILDING_SCALE_RANGE.min || buildingScale > BUILDING_SCALE_RANGE.max) throw new Error("不支持的建筑实验比例");
  const spacing = tileSpacing(tileGap);
  const horizontalScale = new Vector3(spacing, 1, spacing);
  const config = validateMapConfig(input); const topology = buildTopology(config.tiles);
  const vertices = new Map(topology.vertices.map(v => [v.id, { x: v.u * 1.5 * spacing, y: v.v * 1.5 * Math.sqrt(3) * spacing }]));
  const tiles = new Map<string, Matrix4>(); const placements: Placement[] = [];
  for (const tile of config.tiles) {
    const matrix = transform(4.5 * tile.q * spacing, 3 * Math.sqrt(3) * (tile.r + tile.q / 2) * spacing);
    tiles.set(tile.id, matrix);
    placements.push({ asset: TERRAIN_ASSETS[tile.terrain], matrix, tileId: tile.id }, { asset: "map-support-hex", matrix: matrix.clone().scale(horizontalScale) });
  }
  const ports = new Map(config.harbors.map(port => [port.edgeId, port]));
  const incoming = new Map(topology.coast.map(edge => [edge.b, edge]));
  const outgoing = new Map(topology.coast.map(edge => [edge.a, edge]));
  const portPolygons: Vector3[][] = [];
  for (const edge of topology.coast) {
    const a = vertices.get(edge.a)!; const b = vertices.get(edge.b)!;
    const angle = Math.atan2(b.y - a.y, b.x - a.x);
    // Experiment only: stretch the coastal assembly consistently to keep its joins and port sockets aligned.
    const matrix = transform((a.x + b.x) / 2, (a.y + b.y) / 2, 0, angle).scale(horizontalScale);
    const port = ports.get(edge.id);
    placements.push({ asset: port ? "coast-edge-harbor" : "coast-edge", matrix });
    if (port) {
      placements.push({ asset: "harbor", matrix }, { asset: `harbor-marker-${port.kind}`, matrix });
      portPolygons.push(([[-1.24, 0], [1.24, 0], [1.24, 1.975], [-1.24, 1.975]] as const)
        .map(([x, y]) => new Vector3(x, 0, -y).applyMatrix4(matrix)));
    }
  }
  for (const [id, edge] of incoming) {
    const next = outgoing.get(id); if (!next) throw new Error("海岸未闭合");
    const a = vertices.get(edge.a)!; const b = vertices.get(id)!; const c = vertices.get(next.b)!;
    const angle = Math.atan2(b.y - a.y, b.x - a.x);
    const cross = (b.x - a.x) * (c.y - b.y) - (b.y - a.y) * (c.x - b.x);
    placements.push({ asset: cross < 0 ? "coast-corner-convex" : "coast-corner-concave", matrix: transform(b.x, b.y, 0, angle).scale(horizontalScale) });
  }
  // Reject intersecting port envelopes, including those colliding with a different land tile.
  const landPolygons = config.tiles.map(tile => Array.from({ length: 6 }, (_, i) =>
    new Vector3(3 * Math.cos(i * Math.PI / 3), 0, -3 * Math.sin(i * Math.PI / 3)).applyMatrix4(tiles.get(tile.id)!)));
  for (let i = 0; i < portPolygons.length; i++) {
    const polygon = portPolygons.at(i);
    if (!polygon) throw new Error("港口占地缺失");
    if (landPolygons.some(p => polygonsOverlap(polygon, p)) ||
      portPolygons.slice(i + 1).some(p => polygonsOverlap(polygon, p))) throw new Error("港口占地与陆地或其他港口冲突");
  }
  const radius = Math.max(150, Math.max(...[...vertices.values()].map(v => Math.hypot(v.x, v.y))) + 12);
  placements.push({ asset: "sea-surface", matrix: transform(0, 0, -.22).scale(new Vector3(radius, 1, radius)) });
  if (showPieces) {
    const edges = topology.edges.filter(edge => edge.tileIds.length === 2).slice(0, 3);
    for (const edge of edges) {
      const a = vertices.get(edge.a)!; const b = vertices.get(edge.b)!;
      placements.push({ asset: "road", color, matrix: transform((a.x + b.x) / 2, (a.y + b.y) / 2, 0, Math.atan2(b.y - a.y, b.x - a.x)).scale(new Vector3(spacing, 1, 1)) });
    }
    for (const [i, edge] of edges.slice(0, 2).entries()) {
      const v = vertices.get(edge.a)!;
      // Preview-only scale about the ground anchor; leave roads, terrain and layout unchanged.
      placements.push({ asset: i === 0 ? "settlement" : "city", color,
        matrix: transform(v.x, v.y).scale(new Vector3(buildingScale, buildingScale, buildingScale)) });
    }
  }
  return { placements, tiles, coastCount: topology.coast.length };
}

export function polygonsOverlap(a: Vector3[], b: Vector3[]): boolean {
  for (const polygon of [a, b]) for (let i = 0; i < polygon.length; i++) {
    const p = polygon.at(i); const q = polygon.at((i + 1) % polygon.length);
    if (!p || !q) throw new Error("无效占地多边形");
    const axis = new Vector3(-(q.z - p.z), 0, q.x - p.x).normalize();
    const aa = a.map(v => v.dot(axis)); const bb = b.map(v => v.dot(axis));
    if (Math.max(...aa) <= Math.min(...bb) + 1e-5 || Math.max(...bb) <= Math.min(...aa) + 1e-5) return false;
  }
  return true;
}
