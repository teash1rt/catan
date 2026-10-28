import { HIGHLIGHT_PRESETS } from "./board/palettes.ts";
import type { HighlightPalette } from "./board/palettes.ts";

const COLOR_FIELDS: readonly [keyof HighlightPalette, string][] = [
  ["hover", "悬停角标"],
  ["selected", "选中边框"],
  ["accent", "选中角标"],
  ["backing", "底边"],
];

type Props = {
  palette: HighlightPalette;
  onChange: (palette: HighlightPalette) => void;
};

export function HighlightControls({ palette, onChange }: Props): React.JSX.Element {
  const current = HIGHLIGHT_PRESETS.find((preset) =>
    COLOR_FIELDS.every(([key]) => preset.colors[key] === palette[key]),
  );
  return (
    <details className="highlight-controls" open>
      <summary>
        高亮配色 <span>{current?.name ?? "自定义"}</span>
      </summary>
      <p className="palette-hint">先选中地块再切换，移回棋盘查看悬停。</p>
      <div className="palette-presets" role="group" aria-label="高亮配色预设">
        {HIGHLIGHT_PRESETS.map((preset) => (
          <button
            key={preset.name}
            aria-pressed={current === preset}
            onClick={() => onChange(preset.colors)}
          >
            <span className="palette-samples" aria-hidden="true">
              <i style={{ backgroundColor: preset.colors.hover }} />
              <i style={{ backgroundColor: preset.colors.selected }} />
            </span>
            {preset.name}
          </button>
        ))}
      </div>
      <div className="palette-colors">
        {COLOR_FIELDS.map(([key, label]) => (
          <label key={key}>
            <span>{label}</span>
            <input
              type="color"
              aria-label={`${label}颜色`}
              value={palette[key]}
              onChange={(event) => onChange({ ...palette, [key]: event.target.value })}
            />
            <code>{palette[key]}</code>
          </label>
        ))}
      </div>
    </details>
  );
}
