import assert from "node:assert/strict";
import test from "node:test";
import { OrthographicCamera, Plane, Raycaster, Vector2, Vector3 } from "three";
import { BoardCamera, bindCameraInput } from "../src/renderer/src/board/camera.ts";

function setup() {
  const camera = new OrthographicCamera(-20, 20, 14, -14, .1, 150);
  return { camera, control: new BoardCamera(camera) };
}
function settle(control) {
  for (let i = 0; i < 300; i++) if (!control.step(1 / 60)) return;
  assert.fail("camera must settle and stop requesting frames");
}
function ground(camera, ndc) {
  const ray = new Raycaster(); ray.setFromCamera(ndc, camera);
  return ray.ray.intersectPlane(new Plane(new Vector3(0, 1, 0), 0), new Vector3());
}

void test("rotation eases, stays above ground, and settles identically at 30/60/144 Hz", () => {
  const poses = [30, 60, 144].map(fps => {
    const { camera, control } = setup(); const initial = camera.position.clone();
    control.rotate(120, 50); assert.deepEqual(camera.position, initial);
    for (let i = 0; i < fps / 2; i++) control.step(1 / fps);
    return camera.position.clone();
  });
  assert.ok(poses[0].distanceTo(poses[1]) < 1e-9);
  assert.ok(poses[1].distanceTo(poses[2]) < 1e-9);
  const { camera, control } = setup();
  for (const dy of [-1e6, 1e6]) {
    control.rotate(0, dy); settle(control);
    const angle = camera.position.clone().sub(control.target).angleTo(new Vector3(0, 1, 0));
    assert.ok(angle >= Math.PI / 7.2 - 1e-9 && angle <= Math.PI / 3 + 1e-9);
  }
});

void test("right-drag follows ground, cursor zoom stays anchored, bounds and reset are stable", () => {
  const { camera, control } = setup();
  const from = new Vector2(.1, .1), to = new Vector2(.3, .2);
  const point = ground(camera, from);
  control.pan(from, to); settle(control);
  assert.ok(point.distanceTo(ground(camera, to)) < 1e-8);
  assert.equal(control.target.y, 0);
  const cursor = new Vector2(.25, -.15), before = ground(camera, cursor);
  control.zoomAt(cursor, -120);
  assert.equal(camera.zoom, 1); control.step(1 / 60);
  assert.ok(camera.zoom > 1 && camera.zoom < Math.exp(.18)); settle(control);
  assert.ok(before.distanceTo(ground(camera, cursor)) < 1e-8);
  for (let i = 0; i < 100; i++) control.zoomAt(cursor, -240);
  settle(control); assert.ok(Math.abs(camera.zoom - 3.5) < 1e-9);
  for (let i = 0; i < 100; i++) control.zoomAt(cursor, 240);
  settle(control); assert.ok(Math.abs(camera.zoom - .7) < 1e-9);
  control.pan(new Vector2(-50, -50), new Vector2(50, 50)); settle(control);
  assert.ok(control.target.length() <= 16 + 1e-9);
  control.rotate(10000, 100); control.reset(); settle(control);
  assert.ok(camera.position.distanceTo(new Vector3(10, 33, 24)) < 1e-8);
  assert.equal(camera.zoom, 1); assert.equal(control.step(1 / 60), false);
});

class TestCanvas extends EventTarget {
  tabIndex = -1;
  style = { cursor: "" };
  clientHeight = 600;
  ownerDocument = { defaultView: new EventTarget() };
  captured = null;
  focus() {}
  getBoundingClientRect() { return { left: 0, top: 0, width: 800, height: 600 }; }
  setPointerCapture(id) { this.captured = id; }
  hasPointerCapture(id) { return this.captured === id; }
  releasePointerCapture() { this.captured = null; }
}
function dispatch(target, type, props = {}) {
  const event = new Event(type, { cancelable: true });
  Object.assign(event, { pointerType: "mouse", pointerId: 1, button: 0, clientX: 400, clientY: 300 }, props);
  target.dispatchEvent(event); return event;
}

void test("input maps middle rotation/right pan, ignores left drag, normalizes wheel, and cleans up", () => {
  const canvas = new TestCanvas(), calls = [];
  const control = { rotate: (...args) => calls.push(["rotate", ...args]), pan: () => calls.push(["pan"]), zoomAt: (_, px) => calls.push(["zoom", px]) };
  let frames = 0;
  const binding = bindCameraInput(canvas, control, () => { frames++; });
  dispatch(canvas, "pointerdown"); dispatch(canvas, "pointermove", { clientX: 450 }); assert.equal(calls.length, 0);
  dispatch(canvas, "pointerdown", { button: 1 });
  dispatch(canvas, "pointermove", { clientX: 401 }); assert.equal(calls.length, 0);
  dispatch(canvas, "pointermove", { clientX: 450 }); assert.deepEqual(calls.pop(), ["rotate", 50, 0]);
  dispatch(canvas, "pointerup", { button: 1 }); assert.equal(canvas.captured, null);
  dispatch(canvas, "pointerdown", { button: 2 }); dispatch(canvas, "pointermove", { clientX: 460 });
  assert.deepEqual(calls.pop(), ["pan"]); dispatch(canvas, "pointercancel");
  assert.ok(dispatch(canvas, "wheel", { deltaMode: 1, deltaY: 3 }).defaultPrevented);
  assert.deepEqual(calls.pop(), ["zoom", 48]);
  dispatch(canvas, "keydown", { code: "KeyW" }); assert.ok(binding.keys.has("KeyW"));
  dispatch(canvas, "blur"); assert.equal(binding.keys.size, 0);
  dispatch(canvas, "keydown", { code: "KeyQ", metaKey: true }); assert.equal(binding.keys.size, 0);
  binding.dispose(); const count = frames;
  dispatch(canvas, "wheel", { deltaMode: 0, deltaY: 120 }); assert.equal(frames, count);
  assert.equal(canvas.tabIndex, -1); assert.equal(canvas.style.cursor, "");
});
