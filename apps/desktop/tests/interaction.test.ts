import assert from "node:assert/strict";
import test from "node:test";
import { OrthographicCamera, Vector2, Vector3 } from "three";
import { createClassicMap } from "@catan/game-core";
import { BOARD_PRESENTATION, createLayout } from "../src/renderer/src/board/layout.ts";
import {
  bindBoardInput,
  boardTargets,
  pickBoardTarget,
} from "../src/renderer/src/board/interaction.ts";
import type { BoardTarget } from "../src/renderer/src/board/interaction.ts";

const viewport = { left: 30, top: 20, width: 1000, height: 700 };
const targets = boardTargets(
  createLayout(createClassicMap(42), false, undefined, undefined, BOARD_PRESENTATION.tileGap),
);
function screen(target: BoardTarget, camera: OrthographicCamera): Vector2 {
  const point = new Vector3().setFromMatrixPosition(target.matrix).project(camera);
  return new Vector2(
    viewport.left + ((point.x + 1) * viewport.width) / 2,
    viewport.top + ((1 - point.y) * viewport.height) / 2,
  );
}

void test("logical slots remain unique and picking follows rotation, tilt and zoom", () => {
  assert.equal(targets.filter((target) => target.kind === "tile").length, 19);
  assert.equal(targets.filter((target) => target.kind === "edge").length, 72);
  assert.equal(targets.filter((target) => target.kind === "vertex").length, 54);
  assert.equal(
    new Set(targets.map((target) => `${target.kind}/${target.id}`)).size,
    targets.length,
  );
  for (const zoom of [0.7, 1, 3.5]) {
    for (const position of [
      [10, 33, 24],
      [-30, 20, 10],
      [0, 40, -20],
    ]) {
      const camera = new OrthographicCamera(-20, 20, 14, -14, 0.1, 150);
      camera.position.fromArray(position);
      camera.zoom = zoom;
      camera.lookAt(0, 0, 0);
      camera.updateProjectionMatrix();
      camera.updateMatrixWorld();
      for (const kind of ["tile", "edge", "vertex"] as const) {
        const target = targets
          .filter((candidate) => candidate.kind === kind)
          .toSorted(
            (a, b) =>
              new Vector3().setFromMatrixPosition(a.matrix).lengthSq() -
              new Vector3().setFromMatrixPosition(b.matrix).lengthSq(),
          )[0];
        assert.ok(target);
        const point = screen(target, camera);
        const mode = kind === "edge" ? "road" : kind === "vertex" ? "settlement" : "select";
        assert.equal(pickBoardTarget(targets, camera, point, viewport, mode), target);
        if (kind === "vertex") {
          assert.equal(
            pickBoardTarget(
              targets,
              camera,
              point.clone().add(new Vector2(6, 0)),
              viewport,
              "city",
            ),
            target,
          );
          assert.equal(pickBoardTarget(targets, camera, point, viewport, "select"), target);
        }
      }
      assert.equal(pickBoardTarget(targets, camera, new Vector2(-1, -1), viewport, "select"), null);
    }
  }
});

void test("selection respects hex silhouettes and preview modes only target matching slots", () => {
  const camera = new OrthographicCamera(-20, 20, 14, -14, 0.1, 150);
  camera.position.set(10, 33, 24);
  camera.lookAt(0, 0, 0);
  camera.updateMatrixWorld();
  const tile = targets.find((target) => target.kind === "tile" && target.id === "0,0");
  assert.ok(tile);
  const point = screen(tile, camera);
  assert.equal(pickBoardTarget(targets, camera, point, viewport, "road"), null);
  assert.equal(pickBoardTarget(targets, camera, point, viewport, "settlement"), null);
  assert.equal(pickBoardTarget(targets, camera, new Vector2(35, 25), viewport, "select"), null);
  const projected = new Vector3(2.8, 0, 2.3).project(camera);
  const outsideHex = new Vector2(
    viewport.left + ((projected.x + 1) * viewport.width) / 2,
    viewport.top + ((1 - projected.y) * viewport.height) / 2,
  );
  assert.equal(pickBoardTarget([tile], camera, outsideHex, viewport, "select"), null);
});

class TestCanvas extends EventTarget {
  ownerDocument = { defaultView: new EventTarget() };
}
function dispatch(target: EventTarget, type: string, props: Record<string, unknown> = {}): void {
  const event = new Event(type);
  Object.assign(
    event,
    { pointerType: "mouse", pointerId: 7, button: 0, buttons: 0, clientX: 400, clientY: 300 },
    props,
  );
  target.dispatchEvent(event);
}

void test("left clicks select; drags, camera gestures, chorded buttons and canceled input do not", () => {
  const canvas = new TestCanvas();
  // oxlint-disable-next-line typescript/no-unsafe-type-assertion -- 输入测试替身只需要事件与所属窗口。
  const element = canvas as unknown as HTMLCanvasElement;
  let clicks = 0;
  let clears = 0;
  let frames = 0;
  const binding = bindBoardInput(
    element,
    () => {
      frames++;
    },
    () => {
      clicks++;
    },
    () => {
      clears++;
    },
  );
  dispatch(canvas, "pointermove");
  assert.deepEqual(binding.point, new Vector2(400, 300));
  dispatch(canvas.ownerDocument.defaultView, "pointerup");
  assert.equal(binding.point, null);
  dispatch(canvas, "pointerdown", { buttons: 1 });
  dispatch(canvas, "pointerup");
  assert.equal(clicks, 1);
  dispatch(canvas, "pointerdown", { buttons: 1 });
  dispatch(canvas, "pointermove", { buttons: 1, clientX: 420 });
  dispatch(canvas, "pointermove", { buttons: 1 });
  dispatch(canvas, "pointerup");
  assert.equal(clicks, 1);
  for (const button of [1, 2]) {
    dispatch(canvas, "pointerdown", { button, buttons: button === 1 ? 4 : 2 });
    assert.equal(binding.point, null);
    assert.equal(binding.navigating, true);
    dispatch(canvas, "pointermove", { button, buttons: button === 1 ? 4 : 2 });
    dispatch(canvas, "pointerup", { button });
  }
  assert.equal(clicks, 1);
  dispatch(canvas, "pointerdown", { buttons: 1 });
  dispatch(canvas, "pointermove", { buttons: 3 });
  dispatch(canvas, "pointerup");
  assert.equal(clicks, 1);
  for (const event of ["pointerleave", "pointercancel", "lostpointercapture"]) {
    dispatch(canvas, "pointerdown", { buttons: 1 });
    dispatch(canvas, event);
    dispatch(canvas, "pointerup");
  }
  dispatch(canvas, "pointerdown", { buttons: 1 });
  dispatch(canvas.ownerDocument.defaultView, "blur");
  dispatch(canvas, "pointerup");
  assert.equal(clicks, 1);
  dispatch(canvas.ownerDocument.defaultView, "keydown", { code: "Escape" });
  assert.equal(clears, 1);
  assert.equal(binding.point, null);
  dispatch(canvas, "pointerdown", { pointerType: "touch", buttons: 1 });
  dispatch(canvas, "pointerup", { pointerType: "touch" });
  assert.equal(clicks, 1);
  dispatch(canvas, "pointerdown", { buttons: 1 });
  dispatch(canvas, "pointerup");
  assert.equal(clicks, 2);
  binding.dispose();
  const previousFrames = frames;
  dispatch(canvas, "pointermove");
  dispatch(canvas.ownerDocument.defaultView, "keydown", { code: "Escape" });
  assert.equal(frames, previousFrames);
  assert.equal(clears, 1);
});
