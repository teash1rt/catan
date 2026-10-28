export type HighlightPalette = {
  hover: string;
  selected: string;
  accent: string;
  backing: string;
};

export const DEFAULT_HIGHLIGHT_PALETTE: HighlightPalette = {
  hover: "#fff3d5",
  selected: "#b59862",
  accent: "#fff3d5",
  backing: "#68543b",
};

// 同时保留已试过的配色与低饱和替代方案，方便在相同地形上比较。
export const HIGHLIGHT_PRESETS: readonly { name: string; colors: HighlightPalette }[] = [
  { name: "象牙黄铜", colors: DEFAULT_HIGHLIGHT_PALETTE },
  {
    name: "象牙酒红",
    colors: { hover: "#eee3cd", selected: "#985047", accent: "#e7c6aa", backing: "#49332c" },
  },
  {
    name: "骨白铜绿",
    colors: { hover: "#e8e0ce", selected: "#3f766d", accent: "#bfd5c1", backing: "#243d37" },
  },
  {
    name: "暖白灰蓝",
    colors: { hover: "#f0e7d5", selected: "#526b88", accent: "#c6d5dd", backing: "#303b48" },
  },
  {
    name: "暖金薄荷",
    colors: { hover: "#ffe1a0", selected: "#a9f3dd", accent: "#a9f3dd", backing: "#68543b" },
  },
  {
    name: "青蓝紫色",
    colors: { hover: "#00bfff", selected: "#b56cff", accent: "#b56cff", backing: "#16394a" },
  },
];
