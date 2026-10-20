import { MathUtils, Plane, Raycaster, Vector2, Vector3 } from "three";
import type { OrthographicCamera } from "three";

const GROUND = new Plane(new Vector3(0, 1, 0), 0);
const DISTANCE = Math.hypot(10, 33, 24);
const LIMIT = 16;
const clamp = MathUtils.clamp;
const EMPTY_KEYS: ReadonlySet<string> = new Set();
const position = (event: PointerEvent): Vector2 => new Vector2(event.clientX, event.clientY);
const context = (event: Event): void => event.preventDefault();

/** Ground-anchored strategy camera. Input changes goals; frames ease toward them. */
export class BoardCamera {
  readonly target = new Vector3();
  private goal = new Vector3();
  private yaw = Math.atan2(10, 24);
  private goalYaw = this.yaw;
  private pitch = Math.acos(33 / DISTANCE);
  private goalPitch = this.pitch;
  private zoom = 0;
  private goalZoom = 0;
  private scratch: OrthographicCamera;
  private ray = new Raycaster();
  readonly camera: OrthographicCamera;

  constructor(camera: OrthographicCamera) {
    this.camera = camera;
    this.scratch = camera.clone();
    this.apply(camera, this.target, this.yaw, this.pitch, this.zoom);
  }

  private apply(
    camera: OrthographicCamera,
    target: Vector3,
    yaw: number,
    pitch: number,
    zoom: number,
  ): void {
    camera.position
      .set(Math.sin(yaw) * Math.sin(pitch), Math.cos(pitch), Math.cos(yaw) * Math.sin(pitch))
      .multiplyScalar(DISTANCE)
      .add(target);
    camera.zoom = Math.exp(zoom);
    camera.lookAt(target);
    camera.updateProjectionMatrix();
    camera.updateMatrixWorld();
  }

  private plannedCamera(): OrthographicCamera {
    this.scratch.copy(this.camera);
    this.apply(this.scratch, this.goal, this.goalYaw, this.goalPitch, this.goalZoom);
    return this.scratch;
  }

  private ground(camera: OrthographicCamera, point: Vector2): Vector3 {
    this.ray.setFromCamera(point, camera);
    return this.ray.ray.intersectPlane(GROUND, new Vector3()) ?? this.goal.clone();
  }

  private constrain(): void {
    this.goal.y = 0;
    this.goal.clampLength(0, LIMIT);
  }

  rotate(dx: number, dy: number): void {
    this.goalYaw -= dx * 0.0035;
    // Never reach the top-down singularity or skim through models.
    this.goalPitch = clamp(this.goalPitch - dy * 0.003, Math.PI / 7.2, Math.PI / 3);
  }

  pan(from: Vector2, to: Vector2): void {
    const camera = this.plannedCamera();
    this.goal.add(this.ground(camera, from).sub(this.ground(camera, to)));
    this.constrain();
  }

  zoomAt(point: Vector2, pixels: number): void {
    const before = this.ground(this.plannedCamera(), point);
    this.goalZoom = clamp(
      this.goalZoom - clamp(pixels, -240, 240) * 0.0015,
      Math.log(0.7),
      Math.log(3.5),
    );
    this.goal.add(before.sub(this.ground(this.plannedCamera(), point)));
    this.constrain();
  }

  reset(): void {
    this.goal.set(0, 0, 0);
    // Return along the shortest arc, even after several full revolutions.
    this.goalYaw =
      this.yaw +
      Math.atan2(Math.sin(Math.atan2(10, 24) - this.yaw), Math.cos(Math.atan2(10, 24) - this.yaw));
    this.goalPitch = Math.acos(33 / DISTANCE);
    this.goalZoom = 0;
  }

  step(delta: number, keys: ReadonlySet<string> = EMPTY_KEYS): boolean {
    const dt = clamp(delta, 0, 0.05);
    const horizontal =
      Number(keys.has("KeyD") || keys.has("ArrowRight")) -
      Number(keys.has("KeyA") || keys.has("ArrowLeft"));
    const forward =
      Number(keys.has("KeyW") || keys.has("ArrowUp")) -
      Number(keys.has("KeyS") || keys.has("ArrowDown"));
    const turn = Number(keys.has("KeyQ")) - Number(keys.has("KeyE"));
    const speed =
      (10 * dt) / Math.exp(this.goalZoom) / Math.max(1, Math.hypot(horizontal, forward));
    this.goal.x += (Math.cos(this.goalYaw) * horizontal - Math.sin(this.goalYaw) * forward) * speed;
    this.goal.z +=
      (-Math.sin(this.goalYaw) * horizontal - Math.cos(this.goalYaw) * forward) * speed;
    this.goalYaw += turn * dt;
    this.constrain();
    const alpha = -Math.expm1(-14 * dt);
    this.target.lerp(this.goal, alpha);
    this.yaw += (this.goalYaw - this.yaw) * alpha;
    this.pitch += (this.goalPitch - this.pitch) * alpha;
    this.zoom += (this.goalZoom - this.zoom) * alpha;
    const moving =
      this.target.distanceToSquared(this.goal) > 1e-8 ||
      Math.abs(this.yaw - this.goalYaw) > 1e-5 ||
      Math.abs(this.pitch - this.goalPitch) > 1e-5 ||
      Math.abs(this.zoom - this.goalZoom) > 1e-5;
    if (!moving) {
      this.target.copy(this.goal);
      this.yaw = this.goalYaw;
      this.pitch = this.goalPitch;
      this.zoom = this.goalZoom;
    }
    this.apply(this.camera, this.target, this.yaw, this.pitch, this.zoom);
    return moving || horizontal !== 0 || forward !== 0 || turn !== 0;
  }
}

const CAMERA_KEYS = new Set([
  "KeyW",
  "KeyA",
  "KeyS",
  "KeyD",
  "KeyQ",
  "KeyE",
  "ArrowUp",
  "ArrowDown",
  "ArrowLeft",
  "ArrowRight",
]);

/** Keep events on the canvas: scrolling UI or typing elsewhere must not move the map. */
export function bindCameraInput(
  element: HTMLCanvasElement,
  control: BoardCamera,
  wake: () => void,
): { keys: Set<string>; dispose: () => void } {
  const keys = new Set<string>();
  const oldTabIndex = element.tabIndex;
  const oldCursor = element.style.cursor;
  element.tabIndex = 0;
  let drag: { id: number; button: number; start: Vector2; last: Vector2; active: boolean } | null =
    null;
  const ndc = (point: Vector2): Vector2 => {
    const box = element.getBoundingClientRect();
    return new Vector2(
      ((point.x - box.left) / box.width) * 2 - 1,
      1 - ((point.y - box.top) / box.height) * 2,
    );
  };
  const stop = (): void => {
    const captured = drag;
    drag = null;
    keys.clear();
    element.style.cursor = oldCursor;
    if (captured && element.hasPointerCapture(captured.id))
      element.releasePointerCapture(captured.id);
  };
  const down = (event: PointerEvent): void => {
    if (event.pointerType === "touch") return;
    element.focus({ preventScroll: true });
    if ((event.button !== 1 && event.button !== 2) || drag) return;
    event.preventDefault();
    drag = {
      id: event.pointerId,
      button: event.button,
      start: position(event),
      last: position(event),
      active: false,
    };
    element.setPointerCapture(event.pointerId);
  };
  const move = (event: PointerEvent): void => {
    if (!drag || drag.id !== event.pointerId) return;
    const point = position(event);
    if (!drag.active && point.distanceTo(drag.start) < 3) return;
    drag.active = true;
    if (drag.button === 1) control.rotate(point.x - drag.last.x, point.y - drag.last.y);
    else control.pan(ndc(drag.last), ndc(point));
    drag.last = point;
    element.style.cursor = "grabbing";
    wake();
  };
  const up = (event: PointerEvent): void => {
    if (drag?.id === event.pointerId) stop();
  };
  const wheel = (event: WheelEvent): void => {
    event.preventDefault();
    const unit = event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? element.clientHeight : 1;
    control.zoomAt(ndc(new Vector2(event.clientX, event.clientY)), event.deltaY * unit);
    wake();
  };
  const keydown = (event: KeyboardEvent): void => {
    if (!CAMERA_KEYS.has(event.code) || event.ctrlKey || event.metaKey || event.altKey) return;
    event.preventDefault();
    keys.add(event.code);
    wake();
  };
  const keyup = (event: KeyboardEvent): void => {
    keys.delete(event.code);
  };
  const view = element.ownerDocument.defaultView;
  element.addEventListener("pointerdown", down);
  element.addEventListener("pointermove", move);
  element.addEventListener("pointerup", up);
  element.addEventListener("pointercancel", up);
  element.addEventListener("lostpointercapture", stop);
  element.addEventListener("wheel", wheel, { passive: false });
  element.addEventListener("contextmenu", context);
  element.addEventListener("keydown", keydown);
  element.addEventListener("blur", stop);
  view?.addEventListener("keyup", keyup);
  view?.addEventListener("blur", stop);
  return {
    keys,
    dispose: () => {
      stop();
      element.tabIndex = oldTabIndex;
      element.removeEventListener("pointerdown", down);
      element.removeEventListener("pointermove", move);
      element.removeEventListener("pointerup", up);
      element.removeEventListener("pointercancel", up);
      element.removeEventListener("lostpointercapture", stop);
      element.removeEventListener("wheel", wheel);
      element.removeEventListener("contextmenu", context);
      element.removeEventListener("keydown", keydown);
      element.removeEventListener("blur", stop);
      view?.removeEventListener("keyup", keyup);
      view?.removeEventListener("blur", stop);
    },
  };
}
