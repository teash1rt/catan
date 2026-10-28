import {
  BoxGeometry,
  BufferGeometry,
  DoubleSide,
  Float32BufferAttribute,
  Group,
  Mesh,
  MeshBasicMaterial,
  MeshStandardMaterial,
  RingGeometry,
  Vector3,
} from "three";
import type { Material, Object3D } from "three";
import type { AssetLibrary } from "./assembly.ts";
import type { BoardTarget } from "./interaction.ts";
import { DEFAULT_HIGHLIGHT_PALETTE } from "./palettes.ts";
import type { HighlightPalette } from "./palettes.ts";

// 象牙白与旧黄铜延续微缩棋盘材质，悬停断角、选中完整描边，避免依赖鲜艳颜色区分状态。
const FEEDBACK_ORDER = 10;
const PREVIEW_OPACITY = 0.48;
// 地块半径与道路长度沿用资产契约；提示线宽和角标尺寸仅影响展示。
const MARKER = {
  roadLength: 2.4,
  roadHeight: 0.025,
  roadWidth: 0.12,
  tileRadius: 2.98,
  vertexRadius: 0.54,
  lineWidth: 0.035,
  backingWidth: 0.095,
  cornerLength: 0.42,
  cornerWidth: 0.065,
  circleSegments: 64,
  height: 0.04,
  hoverOpacity: 0.75,
  selectedOpacity: 0.95,
  backingOpacity: 0.4,
} as const;

function markerGeometry(kind: BoardTarget["kind"], width: number): BoxGeometry | RingGeometry {
  if (kind === "edge") {
    return new BoxGeometry(MARKER.roadLength, MARKER.roadHeight, MARKER.roadWidth + width);
  }
  const radius = kind === "tile" ? MARKER.tileRadius : MARKER.vertexRadius;
  return new RingGeometry(
    radius - width / 2,
    radius + width / 2,
    kind === "tile" ? 6 : MARKER.circleSegments,
  );
}

function tileCorner(index: number): Vector3 {
  return new Vector3(
    MARKER.tileRadius * Math.cos((index * Math.PI) / 3),
    MARKER.tileRadius * Math.sin((index * Math.PI) / 3),
    0,
  );
}

/** 六个短角标共享一个网格，作为地图上的定位符号，不覆盖地形内部。 */
function tileCorners(width: number): BufferGeometry {
  const positions: number[] = [];
  for (let index = 0; index < 6; index++) {
    const corner = tileCorner(index);
    for (const offset of [-1, 1]) {
      const neighbor = tileCorner(index + offset);
      const direction = neighbor.clone().sub(corner).normalize();
      const normal = new Vector3(-direction.y, direction.x, 0).multiplyScalar(width / 2);
      const end = corner.clone().addScaledVector(direction, MARKER.cornerLength);
      const a = corner.clone().add(normal);
      const b = corner.clone().sub(normal);
      const c = end.clone().add(normal);
      const d = end.clone().sub(normal);
      for (const point of [a, b, c, c, b, d]) {
        positions.push(point.x, point.y, point.z);
      }
    }
  }
  const geometry = new BufferGeometry();
  geometry.setAttribute("position", new Float32BufferAttribute(positions, 3));
  return geometry;
}

export function targetMarker(
  target: BoardTarget,
  selected: boolean,
  palette: HighlightPalette = DEFAULT_HIGHLIGHT_PALETTE,
): Group {
  const group = new Group();
  group.matrix.copy(target.matrix);
  group.matrixAutoUpdate = false;
  const layers: { geometry: BufferGeometry; color: string; opacity: number }[] = [];
  if (selected || target.kind !== "tile") {
    layers.push(
      {
        geometry: markerGeometry(target.kind, MARKER.backingWidth),
        color: palette.backing,
        opacity: MARKER.backingOpacity,
      },
      {
        geometry: markerGeometry(target.kind, MARKER.lineWidth),
        color: selected ? palette.selected : palette.hover,
        opacity: selected ? MARKER.selectedOpacity : MARKER.hoverOpacity,
      },
    );
  }
  if (target.kind === "tile") {
    layers.push(
      {
        geometry: tileCorners(MARKER.cornerWidth + MARKER.backingWidth),
        color: palette.backing,
        opacity: MARKER.backingOpacity,
      },
      {
        geometry: tileCorners(MARKER.cornerWidth),
        color: selected ? palette.accent : palette.hover,
        opacity: selected ? MARKER.selectedOpacity : MARKER.hoverOpacity,
      },
    );
  }
  for (const [index, layer] of layers.entries()) {
    const material = new MeshBasicMaterial({
      color: layer.color,
      opacity: layer.opacity,
      depthTest: false,
      depthWrite: false,
      transparent: true,
      toneMapped: false,
      side: DoubleSide,
    });
    const mesh = new Mesh(layer.geometry, material);
    if (target.kind !== "edge") {
      mesh.rotation.x = -Math.PI / 2;
    }
    mesh.position.y = MARKER.height;
    mesh.renderOrder = FEEDBACK_ORDER + index;
    group.add(mesh);
  }
  group.userData.dispose = () => {
    for (const mesh of group.children) {
      if (mesh instanceof Mesh) {
        mesh.geometry.dispose();
        mesh.material.dispose();
      }
    }
  };
  return group;
}

/** 预览只共享几何体，克隆材质；移除预览不得释放正式棋盘使用的缓存资源。 */
export function piecePreview(
  assets: AssetLibrary,
  assetId: "road" | "settlement" | "city",
  target: BoardTarget,
  color: string,
  buildingScale: number,
): Group {
  const source = assets.get(assetId);
  if (!source) {
    throw new Error(`缺少模型：${assetId}`);
  }
  const group = new Group();
  group.matrix.copy(target.matrix);
  if (assetId !== "road") {
    group.matrix.scale(new Vector3(buildingScale, buildingScale, buildingScale));
  }
  group.matrixAutoUpdate = false;
  const materials = new Map<Material, Material>();
  const copyMaterial = (original: Material): Material => {
    let copy = materials.get(original);
    if (!copy) {
      copy = original.clone();
      copy.transparent = true;
      copy.opacity = PREVIEW_OPACITY;
      copy.depthWrite = false;
      copy.polygonOffset = true;
      copy.polygonOffsetFactor = -1;
      copy.polygonOffsetUnits = -1;
      if (copy instanceof MeshStandardMaterial && copy.name === "player_color") {
        copy.color.set(color);
      }
      materials.set(original, copy);
    }
    return copy;
  };
  source.traverse((node: Object3D) => {
    if (!(node instanceof Mesh)) {
      return;
    }
    const material = Array.isArray(node.material)
      ? node.material.map(copyMaterial)
      : copyMaterial(node.material);
    const mesh = new Mesh(node.geometry, material);
    mesh.matrix.copy(node.matrixWorld);
    mesh.matrixAutoUpdate = false;
    mesh.renderOrder = FEEDBACK_ORDER - 1;
    group.add(mesh);
  });
  group.userData.dispose = () => {
    materials.forEach((material) => material.dispose());
  };
  return group;
}
