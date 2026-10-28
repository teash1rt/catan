import { Component, useCallback, useEffect, useState } from "react";
import type { ErrorInfo, ReactNode } from "react";
import { createClassicMap } from "@catan/game-core";
import { BoardScene } from "./BoardScene.tsx";
import type { RenderStats } from "./BoardScene.tsx";
import { loadAssets } from "./board/assets.ts";
import type { AssetLibrary } from "./board/assembly.ts";
import { BOARD_PRESENTATION } from "./board/layout.ts";
import type { BoardSelection } from "./BoardInteraction.tsx";
import type { InteractionMode } from "./board/interaction.ts";
import { DEFAULT_HIGHLIGHT_PALETTE } from "./board/palettes.ts";
import { HighlightControls } from "./HighlightControls.tsx";

const INTERACTION_MODES: readonly [InteractionMode, string][] = [
  ["select", "选择"],
  ["road", "道路"],
  ["settlement", "村庄"],
  ["city", "城市"],
];
const TARGET_LABELS = { tile: "地块", edge: "边", vertex: "顶点" } as const;

function newSeed(): number {
  return crypto.getRandomValues(new Uint32Array(1))[0] ?? 0;
}
class SceneBoundary extends Component<{ children: ReactNode }, { error: string | null }> {
  override state: { error: string | null } = { error: null };
  static getDerivedStateFromError(error: Error): { error: string } {
    return { error: error.message };
  }
  override componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error("地图渲染失败", error, info);
  }
  override render(): ReactNode {
    return this.state.error ? (
      <div className="loading error" role="alert">
        <h2>地图暂时无法显示</h2>
        <p>{this.state.error}</p>
        <button onClick={() => location.reload()}>重新加载</button>
      </div>
    ) : (
      this.props.children
    );
  }
}

export function App(): React.JSX.Element {
  const [config, setConfig] = useState(() => createClassicMap(newSeed()));
  const [assets, setAssets] = useState<AssetLibrary | null>(null);
  const [loaded, setLoaded] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [generation, setGeneration] = useState(1);
  const [reset, setReset] = useState(0);
  const [pieces, setPieces] = useState(true);
  const [color, setColor] = useState("#b95843");
  const [debugOpen, setDebugOpen] = useState(true);
  const [stats, setStats] = useState<RenderStats | null>(null);
  const [mode, setMode] = useState<InteractionMode>("select");
  const [selection, setSelection] = useState<BoardSelection>(null);
  const [palette, setPalette] = useState(DEFAULT_HIGHLIGHT_PALETTE);
  const onStats = useCallback((value: RenderStats) => setStats(value), []);
  useEffect(() => {
    let active = true;
    setError(null);
    void loadAssets((n) => {
      if (active) setLoaded(n);
    })
      .then((library) => {
        if (active) {
          setAssets(library);
          setLoaded(library.size);
        }
      })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : String(reason));
      });
    return () => {
      active = false;
    };
  }, [attempt]);
  const refresh = (): void => {
    try {
      let seed = newSeed();
      if (seed === config.seed) seed = (seed + 1) >>> 0;
      setConfig(createClassicMap(seed));
      setGeneration((n) => n + 1);
      setError(null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    }
  };
  return (
    <main
      className="app"
      data-map-seed={config.seed}
      data-map-generation={generation}
      data-building-scale={BOARD_PRESENTATION.buildingScale}
      data-tile-gap={BOARD_PRESENTATION.tileGap}
      data-map-config={JSON.stringify(config)}
      data-draw-calls={stats?.calls}
      data-textures={stats?.textures}
      data-geometries={stats?.geometries}
      data-interaction-mode={mode}
      data-selected-kind={selection?.kind}
      data-selected-id={selection?.id}
    >
      <section className="map-panel" aria-label="三维卡坦地图">
        <SceneBoundary>
          {assets && (
            <BoardScene
              assets={assets}
              config={config}
              pieces={pieces}
              color={color}
              {...BOARD_PRESENTATION}
              reset={reset}
              onStats={onStats}
              mode={mode}
              onSelection={setSelection}
              palette={palette}
            />
          )}
        </SceneBoundary>
        {!assets && (
          <div className="loading" role={error ? "alert" : "status"}>
            <h2>{error ? "资源加载失败" : "正在加载地图"}</h2>
            <p>{error ?? `${loaded} / 24`}</p>
            {error && <button onClick={() => setAttempt((n) => n + 1)}>重试加载</button>}
          </div>
        )}
        {assets && error && (
          <div className="notice" role="alert">
            {error}
          </div>
        )}
      </section>
      <aside className={`debug-panel${debugOpen ? "" : " collapsed"}`} aria-label="地图调试">
        <button
          className="debug-toggle"
          aria-expanded={debugOpen}
          aria-controls="debug-controls"
          onClick={() => setDebugOpen((open) => !open)}
        >
          <span>调试</span>
          <span aria-hidden="true">{debugOpen ? "−" : "+"}</span>
        </button>
        <div id="debug-controls" hidden={!debugOpen}>
          <div className="debug-actions">
            <button className="primary" onClick={refresh} disabled={!assets}>
              刷新地图
            </button>
            <button onClick={() => setReset((n) => n + 1)} disabled={!assets}>
              复位视角
            </button>
          </div>
          <div className="interaction-modes" role="group" aria-label="棋盘交互模式">
            {INTERACTION_MODES.map(([value, label]) => (
              <button
                key={value}
                aria-pressed={mode === value}
                disabled={!assets}
                onClick={() => setMode(value)}
              >
                {label}
              </button>
            ))}
          </div>
          <p className="selection-status" aria-live="polite">
            {selection ? `已选${TARGET_LABELS[selection.kind]} · ${selection.id}` : "尚未选中位置"}
          </p>
          {mode !== "select" && <p className="preview-hint">仅预览外观，暂不判断建造规则</p>}
          <HighlightControls palette={palette} onChange={setPalette} />
          <label className="piece-toggle">
            <input type="checkbox" checked={pieces} onChange={(e) => setPieces(e.target.checked)} />
            显示棋子
          </label>
          {(pieces || mode !== "select") && (
            <div className="swatches" aria-label="玩家颜色">
              {[
                ["#b95843", "赭红"],
                ["#3b7295", "海蓝"],
                ["#ddd2b5", "象牙白"],
                ["#d48b38", "琥珀"],
              ].map(([value, label]) => (
                <button
                  key={value}
                  aria-label={label}
                  aria-pressed={color === value}
                  style={{ backgroundColor: value }}
                  onClick={() => setColor(value ?? "#b95843")}
                />
              ))}
            </div>
          )}
          <dl className="debug-stats">
            <div>
              <dt>SEED</dt>
              <dd>{config.seed}</dd>
            </div>
            <div>
              <dt>绘制 / 几何 / 纹理</dt>
              <dd>{stats ? `${stats.calls} / ${stats.geometries} / ${stats.textures}` : "—"}</dd>
            </div>
          </dl>
          <p className="controls-hint">中键旋转 · 右键平移 · 滚轮缩放</p>
          <p className="controls-hint">左键选中 · 空白或 Esc 清除</p>
        </div>
      </aside>
    </main>
  );
}
