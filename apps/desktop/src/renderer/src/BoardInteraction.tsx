import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import type { Group } from "three";
import type { MapConfig } from "@catan/protocol";
import { createLayout } from "./board/layout.ts";
import { bindBoardInput, boardTargets, pickBoardTarget } from "./board/interaction.ts";
import type { BoardTarget, InteractionMode } from "./board/interaction.ts";
import type { AssetLibrary } from "./board/assembly.ts";
import { piecePreview, targetMarker } from "./board/feedback.ts";
import type { HighlightPalette } from "./board/palettes.ts";

export type BoardSelection = { kind: BoardTarget["kind"]; id: string } | null;
type Props = {
  assets: AssetLibrary;
  config: MapConfig;
  mode: InteractionMode;
  color: string;
  buildingScale: number;
  tileGap: number;
  onSelection: (selection: BoardSelection) => void;
  palette: HighlightPalette;
};

export function BoardInteraction({
  assets,
  config,
  mode,
  color,
  buildingScale,
  tileGap,
  onSelection,
  palette,
}: Props): React.JSX.Element {
  const { camera, gl, invalidate } = useThree();
  const targets = useMemo(
    () => boardTargets(createLayout(config, false, undefined, undefined, tileGap)),
    [config, tileGap],
  );
  const [hovered, setHovered] = useState<BoardTarget | null>(null);
  const [selected, setSelected] = useState<BoardTarget | null>(null);
  const hover = useRef<BoardTarget | null>(null);
  const input = useRef<ReturnType<typeof bindBoardInput> | null>(null);
  const container = useRef<Group>(null);

  useEffect(() => {
    const canvas = gl.domElement;
    const pick = (point: Parameters<typeof pickBoardTarget>[2]): BoardTarget | null =>
      pickBoardTarget(targets, camera, point, canvas.getBoundingClientRect(), mode);
    hover.current = null;
    setHovered(null);
    setSelected(null);
    onSelection(null);
    input.current = bindBoardInput(
      canvas,
      invalidate,
      (point) => {
        const target = pick(point);
        setSelected(target);
        onSelection(target ? { kind: target.kind, id: target.id } : null);
      },
      () => {
        setSelected(null);
        onSelection(null);
      },
    );
    const binding = input.current;
    return () => {
      binding.dispose();
      input.current = null;
      canvas.style.cursor = "";
    };
  }, [camera, gl, invalidate, targets, mode, onSelection]);

  // 镜头缓动时也重新拾取；空闲时不额外请求帧。
  useFrame(() => {
    const point = input.current?.point;
    const next = point
      ? pickBoardTarget(targets, camera, point, gl.domElement.getBoundingClientRect(), mode)
      : null;
    if (next !== hover.current) {
      hover.current = next;
      setHovered(next);
    }
    if (!input.current?.navigating) {
      gl.domElement.style.cursor = next ? "pointer" : "";
    }
  });

  useLayoutEffect(() => {
    const parent = container.current;
    if (!parent) {
      return undefined;
    }
    const overlays: Group[] = [];
    if (selected) {
      overlays.push(targetMarker(selected, true, palette));
    }
    if (hovered && hovered !== selected) {
      overlays.push(targetMarker(hovered, false, palette));
    }
    const preview = selected ?? hovered;
    if (preview && mode !== "select") {
      overlays.push(piecePreview(assets, mode, preview, color, buildingScale));
    }
    parent.add(...overlays);
    invalidate();
    return () => {
      parent.remove(...overlays);
      overlays.forEach((overlay) => overlay.userData.dispose());
    };
  }, [assets, hovered, selected, mode, color, buildingScale, palette, invalidate]);

  return <group ref={container} dispose={null} />;
}
