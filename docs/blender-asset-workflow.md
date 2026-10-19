# Blender 资产工作流

模块边界与实施顺序见 [可插拔资产实施计划](modular-asset-plan.md)；建模和视觉评审遵循 [Blender 建模 Skill](../.agents/skills/catan-blender-modeling/SKILL.md)。

## 核心原则

Blender 只负责制作资产，不嵌入 Electron，也不与 Electron 直接通信。桌面端只加载 Blender 导出的 GLB：

```text
.blend 源文件 → 导出 .glb → 自动验证 → Electron Renderer / Three.js 加载
```

## 标准流程

1. **制作**：在 Blender 中完成模型、UV、材质和贴图；统一尺寸、原点与命名，并应用 Rotation/Scale。
2. **导出**：导出为单文件 `.glb`。仅导出需要的对象，应用 Modifier，保留 UV、Normal 和材质，不导出相机与灯光。
3. **验证**：检查 glTF 格式、文件大小、面数、贴图尺寸、包围盒及意外节点；错误应阻止合入。
4. **集成**：由 Electron Renderer 中的 React Three Fiber/Three.js 加载 GLB。主进程、IPC、服务端和 `game-core` 不参与资产加载。
5. **复用**：同一 GLB 只加载一次；大量相同树木、建筑使用实例化，不重复加载或复制资源。
6. **验收**：同时检查开发环境和打包后的 Windows/macOS 应用，确认路径、比例、材质、阴影和性能。

地图基座按[基座契约](modular-asset-plan.md#地图基座契约-v12026-10-18)逐组件交付，不把组合样板导成整盘 GLB。布局产生承托、海岸与凹凸角位置，主题映射模型链接；有港口的岸段替换为开槽件。Blender 样板通过不替代运行时验收；当前已接入的 [Electron 地图展示样板](desktop-map-preview.md)单独记录验证范围。

## 目录约定

```text
assets/<asset-id>/
  model.blend                # 可编辑源文件，所需贴图打包在内
  model.glb                  # 游戏运行时模型
scripts/assets/              # 建模、导出和验证脚本
```

每种资产独占一个目录，源文件与运行时文件放在一起，例如 `assets/forest-tile/model.blend` 和 `assets/forest-tile/model.glb`。目录名就是稳定的资产 ID；不要在桌面端另存一份正式 GLB。Electron 通过 Vite 只导入 `assets/*/model.glb`，不打包 `.blend`。正式路径只保留当前一对文件，不设版本目录；`out/` 中的构建副本不属于模型归档，不提交。

## 版本控制

`.blend` 和 `.glb` 已通过 `.gitattributes` 统一使用 Git LFS，代码、脚本和文档使用普通 Git；检查步骤与协作约定见 [资产 Git 上传方案](asset-git-strategy.md)。克隆后先取得真实 LFS 文件，再运行或构建应用。

Python 建模/验证工具不是临时日志，应按[脚本保留清单](../scripts/assets/README.md)分类保留；它们不随 Electron 游戏运行。

### 单模型交付规范

使用稳定的 `<asset-id>`（如 `forest-tile`），正式目录不设版本层级；当前产物和待办见 [模型资产清单](asset-inventory.md)。历史由 Git 管理；未提交的旧模型先备份到项目外，再替换正式产物。

```text
assets/<asset-id>/model.blend  # 唯一当前源文件，所需贴图打包在文件内
assets/<asset-id>/model.glb    # 单文件运行时模型，含约定挂点，不含摄影棚
```

- 模型产物只保留最新 `.blend` 和 `.glb`。不保留 `previews/`、`reviews/` 或默认生成切图；文档与可复用脚本照常保留。
- 视觉评审和技术校验仍须执行；预览、截图、报告放临时目录或保留为会话证据，交付时说明实际检查范围与未完成项。预览图不能冒充 Computer Use 截图。
- 迭代时先保留可恢复版本；新版本交付后将旧产物移出项目。未通过的版本明确标为草稿，不作为可发布资源。
- 草稿使用临时目录；建模脚本通过 `--source /private/tmp/.../draft.blend` 指定，不覆盖已有源文件。评审通过后归档到上述固定路径，并同步导出 GLB；评审脚本的 `--review-dir` 必须指向临时目录。
- 挂点回归：`Blender --background --python-exit-code 1 --python scripts/assets/audit_tile_anchors.py`。只读检查六类源文件与 GLB 的挂点、实际净空和边沿，错误返回非零；不替代视觉评审。

应提交：

- `.blend` 源文件（含打包贴图）；
- 经确认的 `.glb` 运行时资源；
- 导出/验证脚本、资产说明和许可证；
- 大型二进制资源对应的 Git LFS 配置。

不提交：

- `.blend1`、自动保存和恢复文件；
- 预览、切图、评审报告、渲染缓存和临时导出；
- 重复的 FBX、OBJ 等中间格式；
- `dist`、`build`、`node_modules`。

## 自动化边界

Codex 可以按建模 Skill 自动建模、修正、执行 Computer Use 视觉评审、导出及技术校验，也可以实现 GLB 加载与实例化。人工负责审美方向与最终批准，以及许可证确认。建模通过不等于桌面端或打包测试通过。

导出规则稳定后，应使用版本化脚本替代重复的 GUI 导出，保证本地和 CI 得到一致结果。
