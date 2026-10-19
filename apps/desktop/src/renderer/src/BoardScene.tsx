import { useEffect, useLayoutEffect, useRef } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { ACESFilmicToneMapping, OrthographicCamera, PCFShadowMap } from "three";
import type { Group } from "three";
import type { MapConfig } from "@catan/protocol";
import { assembleBoard } from "./board/assembly.ts";
import type { AssetLibrary } from "./board/assembly.ts";
import { createNumbers } from "./board/numbers.ts";
import { BoardCamera, bindCameraInput } from "./board/camera.ts";

export type RenderStats = { calls: number; triangles: number; geometries: number; textures: number };
type Props = { assets: AssetLibrary; config: MapConfig; pieces: boolean; color: string; buildingScale: number; tileGap: number; reset: number; onStats: (stats: RenderStats) => void };

function Models({ assets, config, pieces, color, buildingScale, tileGap }: Props): React.JSX.Element {
  const container = useRef<Group>(null);
  const invalidate = useThree(state => state.invalidate);
  useLayoutEffect(() => {
    const parent = container.current;
    if (!parent) throw new Error("地图容器尚未挂载");
    const board = assembleBoard(assets, config, pieces, color, buildingScale, tileGap);
    const numbers = createNumbers(assets, config, tileGap); board.add(numbers);
    parent.add(board); invalidate();
    // Detach BEFORE disposal: otherwise a demand frame can re-upload the old textures.
    return () => { parent.remove(board); numbers.userData.dispose(); board.userData.dispose(); };
  }, [assets, config, pieces, color, buildingScale, tileGap, invalidate]);
  return <group ref={container} dispose={null} />;
}

function Camera({ reset }: { reset: number }): null {
  const { camera, gl, invalidate, size } = useThree();
  const controls = useRef<BoardCamera | null>(null);
  const keys = useRef<ReadonlySet<string>>(new Set());
  useEffect(() => {
    if (!(camera instanceof OrthographicCamera)) return undefined;
    const control = new BoardCamera(camera);
    const input = bindCameraInput(gl.domElement, control, invalidate);
    controls.current = control; keys.current = input.keys;
    return () => { input.dispose(); controls.current = null; keys.current = new Set(); };
  }, [camera, gl, invalidate]);
  useFrame((_, delta) => { if (controls.current?.step(delta, keys.current)) invalidate(); });
  useEffect(() => {
    if (!(camera instanceof OrthographicCamera)) return;
    const aspect = size.width / size.height;
    const halfHeight = Math.max(13.8, 16.8 / aspect);
    camera.left = -halfHeight * aspect; camera.right = halfHeight * aspect;
    camera.top = halfHeight; camera.bottom = -halfHeight;
    camera.updateProjectionMatrix(); invalidate();
  }, [camera, size, invalidate]);
  useEffect(() => {
    controls.current?.reset(); invalidate();
  }, [reset, invalidate]);
  return null;
}

function Metrics({ onStats }: { onStats: (stats: RenderStats) => void }): null {
  const last = useRef(0);
  useFrame(({ gl, scene, camera }) => {
    gl.render(scene, camera);
    const now = performance.now();
    if (now - last.current < 200) return;
    last.current = now;
    onStats({ calls: gl.info.render.calls, triangles: gl.info.render.triangles,
      geometries: gl.info.memory.geometries, textures: gl.info.memory.textures });
  }, 1);
  return null;
}

export function BoardScene(props: Props): React.JSX.Element {
  return <Canvas orthographic shadows frameloop="demand" dpr={[1, 1.5]}
    camera={{ position: [10, 33, 24], near: .1, far: 150 }}
    gl={{ antialias: true, alpha: false, powerPreference: "high-performance" }}
    onCreated={({ gl }) => { gl.toneMapping = ACESFilmicToneMapping; gl.toneMappingExposure = 1.12; gl.shadowMap.type = PCFShadowMap; }}>
    <color attach="background" args={["#326c7b"]} />
    <hemisphereLight args={["#fff2d8", "#759499", 2.1]} />
    <directionalLight position={[-12, 28, 12]} intensity={3.0} color="#ffefd4" castShadow
      shadow-mapSize={[2048, 2048]} shadow-camera-left={-20} shadow-camera-right={20}
      shadow-camera-top={20} shadow-camera-bottom={-20} shadow-camera-near={1} shadow-camera-far={70}
      shadow-bias={-.00012} shadow-normalBias={.035} shadow-radius={3} />
    <directionalLight position={[12, 10, -8]} intensity={1.0} color="#dfedff" />
    <Models {...props} />
    <Camera reset={props.reset} />
    <Metrics onStats={props.onStats} />
  </Canvas>;
}
