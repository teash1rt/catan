import { Plane, Raycaster, Vector2, Vector3 } from "three";
import type { Camera, Matrix4 } from "three";
import type { BoardLayout } from "./layout.ts";

export type InteractionMode = "select" | "road" | "settlement" | "city";
export type BoardTarget = { kind: "tile" | "edge" | "vertex"; id: string; matrix: Matrix4 };
export type Viewport = { left: number; top: number; width: number; height: number };

// 拾取容差使用屏幕像素，保证拉远后边与顶点仍容易命中。
const VERTEX_HIT_PIXELS = 14;
const EDGE_HIT_PIXELS = 10;
const CLICK_SLOP_PIXELS = 4;
// 与地块半径 3、边长 3 的资产契约保持一致。
const TILE_RADIUS = 3;
const EDGE_HALF_LENGTH = 1.5;
// PointerEvent.buttons 中，右键为 2，中键为 4。
const CAMERA_BUTTON_MASK = 6;
const GROUND = new Plane(new Vector3(0, 1, 0), 0);
const position = (event: PointerEvent): Vector2 => new Vector2(event.clientX, event.clientY);

export function boardTargets(layout: BoardLayout): BoardTarget[] {
  return [
    ...[...layout.slots.vertices].map(([id, matrix]) => ({ kind: "vertex" as const, id, matrix })),
    ...[...layout.slots.edges].map(([id, matrix]) => ({ kind: "edge" as const, id, matrix })),
    ...[...layout.tiles].map(([id, matrix]) => ({ kind: "tile" as const, id, matrix })),
  ];
}

function segmentDistance(point: Vector2, a: Vector2, b: Vector2): number {
  const direction = b.clone().sub(a);
  const fraction = Math.max(
    0,
    Math.min(1, point.clone().sub(a).dot(direction) / direction.lengthSq()),
  );
  return point.distanceTo(a.clone().addScaledVector(direction, fraction));
}

/** 逻辑插槽独立于模型网格；选择模式按顶点、边、地块的顺序命中。 */
export function pickBoardTarget(
  targets: readonly BoardTarget[],
  camera: Camera,
  point: Vector2,
  viewport: Viewport,
  mode: InteractionMode,
): BoardTarget | null {
  const { left, top, width, height } = viewport;
  if (point.x < left || point.y < top || point.x > left + width || point.y > top + height) {
    return null;
  }

  const project = (world: Vector3): Vector2 | null => {
    const projected = world.clone().project(camera);
    if (projected.z < -1 || projected.z > 1) {
      return null;
    }
    return new Vector2(
      left + ((projected.x + 1) * width) / 2,
      top + ((1 - projected.y) * height) / 2,
    );
  };

  for (const kind of ["vertex", "edge"] as const) {
    if (
      (mode === "road" && kind !== "edge") ||
      ((mode === "settlement" || mode === "city") && kind !== "vertex")
    ) {
      continue;
    }
    let nearest: BoardTarget | null = null;
    let distance = kind === "vertex" ? VERTEX_HIT_PIXELS : EDGE_HIT_PIXELS;
    for (const target of targets) {
      if (target.kind !== kind) {
        continue;
      }
      const center = project(new Vector3().setFromMatrixPosition(target.matrix));
      if (!center) {
        continue;
      }
      let candidate = point.distanceTo(center);
      if (kind === "edge") {
        const a = project(new Vector3(-EDGE_HALF_LENGTH, 0, 0).applyMatrix4(target.matrix));
        const b = project(new Vector3(EDGE_HALF_LENGTH, 0, 0).applyMatrix4(target.matrix));
        if (!a || !b) {
          continue;
        }
        candidate = segmentDistance(point, a, b);
      }
      if (candidate < distance) {
        nearest = target;
        distance = candidate;
      }
    }
    if (nearest) {
      return nearest;
    }
  }
  if (mode !== "select") {
    return null;
  }

  const ray = new Raycaster();
  ray.setFromCamera(
    new Vector2(((point.x - left) / width) * 2 - 1, 1 - ((point.y - top) / height) * 2),
    camera,
  );
  const ground = ray.ray.intersectPlane(GROUND, new Vector3());
  if (!ground) {
    return null;
  }
  return (
    targets.find((target) => {
      if (target.kind !== "tile") {
        return false;
      }
      const local = ground.clone().applyMatrix4(target.matrix.clone().invert());
      const x = Math.abs(local.x);
      const z = Math.abs(local.z);
      return (
        x <= TILE_RADIUS &&
        z <= (Math.sqrt(3) * TILE_RADIUS) / 2 &&
        Math.sqrt(3) * x + z <= Math.sqrt(3) * TILE_RADIUS
      );
    }) ?? null
  );
}

/** 左键点击与镜头手势分开处理；拖拽、多键组合和取消事件都不得提交选择。 */
export function bindBoardInput(
  element: HTMLCanvasElement,
  wake: () => void,
  select: (point: Vector2) => void,
  clear: () => void,
): { readonly point: Vector2 | null; readonly navigating: boolean; dispose(): void } {
  let point: Vector2 | null = null;
  let left: { id: number; start: Vector2 } | null = null;
  const cameraButtons = new Set<number>();
  const down = (event: PointerEvent): void => {
    if (event.pointerType === "touch") {
      return;
    }
    if (event.button !== 0) {
      cameraButtons.add(event.button);
      left = null;
      point = null;
    } else if (cameraButtons.size === 0 && (event.buttons & CAMERA_BUTTON_MASK) === 0) {
      left = { id: event.pointerId, start: position(event) };
    }
    wake();
  };
  const move = (event: PointerEvent): void => {
    if (event.pointerType === "touch") {
      return;
    }
    const navigating = cameraButtons.size > 0 || (event.buttons & CAMERA_BUTTON_MASK) !== 0;
    point = navigating ? null : position(event);
    if (navigating) {
      left = null;
    }
    if (left && point && point.distanceTo(left.start) > CLICK_SLOP_PIXELS) {
      left = null;
    }
    wake();
  };
  const up = (event: PointerEvent): void => {
    if (event.pointerType === "touch") {
      return;
    }
    if (event.button === 0) {
      if (
        left?.id === event.pointerId &&
        cameraButtons.size === 0 &&
        (event.buttons & CAMERA_BUTTON_MASK) === 0 &&
        position(event).distanceTo(left.start) <= CLICK_SLOP_PIXELS
      ) {
        select(position(event));
      }
      left = null;
    }
    cameraButtons.delete(event.button);
    if (event.buttons === 0) {
      cameraButtons.clear();
    }
    point = cameraButtons.size === 0 ? position(event) : null;
    wake();
  };
  const leave = (): void => {
    point = null;
    left = null;
    wake();
  };
  const cancel = (): void => {
    cameraButtons.clear();
    leave();
  };
  const outsideUp = (event: PointerEvent): void => {
    if (event.target !== element) {
      cancel();
    }
  };
  const key = (event: KeyboardEvent): void => {
    if (event.code === "Escape") {
      cancel();
      clear();
    }
  };
  const view = element.ownerDocument.defaultView;
  element.addEventListener("pointerdown", down);
  element.addEventListener("pointermove", move);
  element.addEventListener("pointerup", up);
  element.addEventListener("pointerleave", leave);
  element.addEventListener("pointercancel", cancel);
  element.addEventListener("lostpointercapture", cancel);
  view?.addEventListener("pointerup", outsideUp);
  view?.addEventListener("blur", cancel);
  view?.addEventListener("keydown", key);
  return {
    get point() {
      return point;
    },
    get navigating() {
      return cameraButtons.size > 0;
    },
    dispose() {
      element.removeEventListener("pointerdown", down);
      element.removeEventListener("pointermove", move);
      element.removeEventListener("pointerup", up);
      element.removeEventListener("pointerleave", leave);
      element.removeEventListener("pointercancel", cancel);
      element.removeEventListener("lostpointercapture", cancel);
      view?.removeEventListener("pointerup", outsideUp);
      view?.removeEventListener("blur", cancel);
      view?.removeEventListener("keydown", key);
    },
  };
}
