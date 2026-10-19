# 模型资产清单

更新：2026-10-18。此处维护当前路径与建模待办；组合契约见 [资产计划](modular-asset-plan.md)，交付规则见 [资产工作流](blender-asset-workflow.md)。不在此累积生成日志。

**最新集成状态**：已实现 [Electron 19 地块＋9 港口展示样板](desktop-map-preview.md)，支持刷新地形/数字、动态数字、玩家换色和实例化；macOS 开发版与构建后本地加载已检查。下文“未实现/未验证 Electron”等描述保留模型交付当时的验收边界，运行时最新结论以展示样板文档为准；不代表 Windows 或安装包通过。

## 已交付地块

每类仅一份源文件和一份运行时 GLB；源文件目录不设版本号。场景内的树木、砖窑、吊机、风车、羊舍等是地块细节，不等于已交付独立建筑模块。

| 地块 | Blender 源文件 | 运行时模型 | 当前造型 |
| --- | --- | --- | --- |
| 森林 | [model.blend](../assets/forest-tile/model.blend) | [model.glb](../assets/forest-tile/model.glb) | 明亮树冠、林地、木料 |
| 砖 | [model.blend](../assets/brick-tile/model.blend) | [model.glb](../assets/brick-tile/model.glb) | 氧化铁红连续山体、红土地面、侧边砖窑 |
| 石 | [model.blend](../assets/stone-tile/model.blend) | [model.glb](../assets/stone-tile/model.glb) | 宽阔蓝灰采石崖、吊机、石材交易场 |
| 麦 | [model.blend](../assets/wheat-tile/model.blend) | [model.glb](../assets/wheat-tile/model.glb) | 起伏麦田、弯曲农路、柔和旧木风车 |
| 羊 | [model.blend](../assets/sheep-tile/model.blend) | [model.glb](../assets/sheep-tile/model.glb) | 浅绿牧场、羊群、茅草羊舍 |
| 沙漠 | [model.blend](../assets/desert-tile/model.blend) | [model.glb](../assets/desert-tile/model.glb) | 空旷暖沙地、连续低缓沙丘，无道具 |

上述资产已有 Computer Use/GLB 回导评审；森林于 2026-10-15 修正挂点地面并复核，保留原画风。砖、石风格已获用户认可；当前麦、羊、沙漠版本仍待最终审美确认。Electron、打包与整盘性能不在已验收范围。

## 已交付独立棋子与标记底座

| 资产 | Blender 源文件 | 运行时模型 | 当前造型 |
| --- | --- | --- | --- |
| 强盗 | [model.blend](../assets/robber/model.blend) | [model.glb](../assets/robber/model.glb) | 黑衣中世纪领主、兜帽遮面、长披风、扶剑站姿 |
| 数字底座 | [model.blend](../assets/number-token/model.blend) | [model.glb](../assets/number-token/model.glb) | 胡桃木薄边、暖象牙色牌面、细金棕描边；数字与概率点独立 |

强盗黑色方案完成基线及一轮修正：Computer Use 检查棋盘、近景、侧面、背面、GLB 回导及六地块挂载，尺寸与导出检查通过；最终审美待用户确认。因 Blender MCP 不可用，本次采用已说明的本地 Blender Python 替代，并非 MCP 闭环验证通过。尚未验证 Electron 实际渲染与性能。

数字底座完成基线及一轮修正（降低文字挂点，消除悬浮感）：Computer Use 检查近景、侧面、棋盘、1–12 排版、GLB 回导及六地块挂载，森林另测数字移除与替换为 12；底座与强盗互不遮挡，尺寸、挂点及导出检查通过。GLB 约 91 KB，只含空白底座与内容挂点；数字/概率点仅为临时评审内容，Electron 动态文字尚未实现。采用已说明的本地 Blender Python 替代，MCP 闭环未验证；最终审美待用户确认。沙漠挂载仅用于契约测试，标准玩法仍不放数字。

## 已交付顶点建筑

| 资产 | Blender 源文件 | 运行时模型 | 当前造型 |
| --- | --- | --- | --- |
| 村庄 | [model.blend](../assets/settlement/model.blend) | [model.glb](../assets/settlement/model.glb) | 木梁灰泥民居、厚瓦顶、拱窗与石烟囱 |
| 城市 | [model.blend](../assets/city/model.blend) | [model.glb](../assets/city/model.glb) | 石砌门楼、尖顶旗帜与错落侧厅，非村庄放大版 |

每类只保留一套模型；`player_color` 控制屋顶和城市旗帜，支持输入颜色换皮，墙面、石材、木梁保持不变。落脚与换色接口见 [顶点建筑契约](modular-asset-plan.md#顶点建筑契约-v12026-10-17)。建筑是顶点棋子，尺寸小于地块内叙事性建筑；不能为放大外观而直接突破接缝预留带。

完成基线及两轮修正；Computer Use 检查近景、侧面、背面、棋盘尺度、红/蓝/象牙白/橙配色和 GLB 回导。森林＋麦＋羊的单个共享顶点组合用于原位升级检查，不代表全地图验收。源文件与 GLB 占地/原点/材质槽检查通过；村庄 `29,979` 三角面、约 `2.10 MB`，城市 `57,059` 三角面、约 `3.98 MB`，均为 2 网格、9 材质，无外部贴图及展示相机/灯光。当前是近景资产统计，尚未通过整盘性能或 LOD 验收。

工具为已说明的本地 Blender Python 替代＋Computer Use，MCP 闭环未验证。Electron 动态换色、实例化、整盘道路衔接、Windows/macOS 打包均未实现或验证；最终审美待用户确认。复现脚本：`scripts/assets/create_vertex_buildings.py`。

## 已交付道路

| 资产 | Blender 源文件 | 运行时模型 | 当前造型 |
| --- | --- | --- | --- |
| 道路 | [model.blend](../assets/road/model.blend) | [model.glb](../assets/road/model.glb) | 暖灰石铺路面、细木边、可换色路缘 |

`player_color` 只控制两侧路缘，与建筑使用同一换色接口；一套模型支持不同玩家，不按颜色复制文件。边中点原点、逻辑端点和建筑避让见 [道路契约](modular-asset-plan.md#道路契约-v12026-10-17)。`7,884` 三角面、2 网格、6 材质，GLB `558,940` 字节；无外部贴图、展示相机或灯光。复现脚本：`scripts/assets/create_road.py`。

2026-10-17 补完 Computer Use 基线评审并归档；本轮未修改造型（0 轮造型修正）。实际检查近景、侧面、棋盘、四配色、独立 GLB 回导，以及森林＋麦＋羊的空顶点／村庄／城市三岔口；另加入临时数字内容和独立强盗作尺度对照。源文件与 GLB 的尺寸、挂点、材质隔离和端点对齐检查通过；基本 GLB 结构检查通过，未运行完整 Khronos 校验器。截图保留在会话，不进入正式资产目录。

**验收边界**：俯视下道路与建筑、装饰占地分离；约 66° 棋盘视角下该样板道路与数字可辨，但从牧场方向的低角度近景会遮挡局部道路和城市底部，低角度可读性未通过，不代表全地图／全镜头验收。本轮未改羊地块；后续确定游戏镜头后处理遮挡策略。使用本地 Blender Python 替代＋Computer Use，MCP 闭环未验证；Electron 加载／换色／实例化、整盘性能及打包未验证，最终审美待用户确认。

## 已交付港口与交易牌

沿用[桌游版](https://www.catan.com/catan)的海岸泊位、帆船和交易标记识别方式，做成暖木色、亚麻白帆的中世纪微缩造型；不分发官方贴图。主体与六种标记独立，通过 `anchor_trade` 组合，接口见[港口契约](modular-asset-plan.md#港口契约-v12026-10-18)。`3:1` 通用与 `2:1` 资源港规则依据[官方规则](https://www.catan.com/sites/default/files/2021-06/catan_base_rules_2020_200707.pdf)，规则仍由配置决定。

| 资产 | Blender 源文件 | 运行时模型 |
| --- | --- | --- |
| 港口主体 | [model.blend](../assets/harbor/model.blend) | [model.glb](../assets/harbor/model.glb) |
| 通用 3:1 | [model.blend](../assets/harbor-marker-generic/model.blend) | [model.glb](../assets/harbor-marker-generic/model.glb) |
| 木材 2:1 | [model.blend](../assets/harbor-marker-lumber/model.blend) | [model.glb](../assets/harbor-marker-lumber/model.glb) |
| 砖 2:1 | [model.blend](../assets/harbor-marker-brick/model.blend) | [model.glb](../assets/harbor-marker-brick/model.glb) |
| 矿石 2:1 | [model.blend](../assets/harbor-marker-ore/model.blend) | [model.glb](../assets/harbor-marker-ore/model.glb) |
| 麦 2:1 | [model.blend](../assets/harbor-marker-grain/model.blend) | [model.glb](../assets/harbor-marker-grain/model.glb) |
| 羊毛 2:1 | [model.blend](../assets/harbor-marker-wool/model.blend) | [model.glb](../assets/harbor-marker-wool/model.glb) |

主体 `20,792` 三角面、7 材质、`1,067,488` 字节；每种牌 `2,900–6,320` 三角面、3–5 材质、约 `0.10–0.36 MB`。每份 GLB 为 1 网格，主体另含 3 挂点；均无外部图片/字体、展示相机、灯光和动画。不是整盘性能预算结论。

完成基线＋**1 轮修正**：补登岸板，消除岸边水缝，同时为小旗增加厚度。Computer Use 实查近景、侧面、棋盘尺度、六种牌及独立 GLB 回导；麦地块＋数字＋村庄/城市＋可移除道路样板确认接岸与建筑避让。源文件/回导尺寸、有限坐标/法线、三角面、挂点、道路占地裁剪及六方向定位通过；基本 GLB 结构检查通过，未运行完整 Khronos 校验器。截图与详细逐轮记录留会话/临时目录。

指令/路径检查完成；视觉检查仅限上述样板，最终审美待用户确认。采用已说明的本地 Blender Python＋Computer Use，Blender MCP 闭环未验证。**未验证 Electron、整盘性能、内凹海湾/相邻港口、正式海岸边框或全镜头可读性**。牌面是固定朝向，从反面观看文字倒置；不宣称自动朝向玩家。

复现：`scripts/assets/create_harbor.py -- --work-dir <项目外临时目录> --mode build|preview|export|composition`（由 Blender 后台执行）；先生成并视觉评审，再导出、回导及组合检查，最后归档。

## 已交付模块化基座与海岸

低矮深木承托、暖砂岩岸沿、哑光蓝绿海面，保持地块为主角。六个独立组件适配既有地块；数值与组合方向见[基座契约](modular-asset-plan.md#地图基座契约-v12026-10-18)，不交付固化整盘 GLB。

| 组件 | Blender 源文件 | 运行时模型 | 三角面 / GLB 字节 |
| --- | --- | --- | --- |
| 地块下承托 | [model.blend](../assets/map-support-hex/model.blend) | [model.glb](../assets/map-support-hex/model.glb) | 44 / 5,288 |
| 普通岸段 | [model.blend](../assets/coast-edge/model.blend) | [model.glb](../assets/coast-edge/model.glb) | 32 / 7,664 |
| 港口开槽岸段 | [model.blend](../assets/coast-edge-harbor/model.blend) | [model.glb](../assets/coast-edge-harbor/model.glb) | 128 / 12,896 |
| 外凸转角 | [model.blend](../assets/coast-corner-convex/model.blend) | [model.glb](../assets/coast-corner-convex/model.glb) | 50 / 8,588 |
| 内凹转角 | [model.blend](../assets/coast-corner-concave/model.blend) | [model.glb](../assets/coast-corner-concave/model.glb) | 50 / 8,548 |
| 可缩放静态海面 | [model.blend](../assets/sea-surface/model.blend) | [model.glb](../assets/sea-surface/model.glb) | 2 / 1,304 |

每份 1 网格；承托 3 材质、岸段/转角 7 材质、海面 1 材质；总计约 44.3 KB。无外部贴图、相机、灯光或动画，正式目录仅最新 `.blend/.glb`。旧地块、港口和棋子文件未修改。

| 评审轮次 | 问题与修改 | 证据 / 结论 |
| --- | --- | --- |
| 基线 | 岸坡立即下落，沿海道路/建筑外侧缺少水平承托 | Computer Use 棋盘、港口近景；落脚需修正 |
| 修正 1 | 加宽水平承托至 0.28；缩短转角接口占长，另做登岸槽，避免木板与岸面共面 | 同近景/中性光照对比；侧面、凹角、回导棋盘及近景、隐藏上层检查空承托；上述范围通过 |

技术检查通过：六份独立回导尺寸/三角面/挂点一致、有限坐标与法线、承托面射线、实际模型端截面对齐、无展示节点。六地块样板 27 条唯一边、22 个唯一顶点、18 条海岸；单/双地块、环形留洞、分离岛屿及 19 地块追加拓扑检查（19 地块为 72 边/54 顶点）。港口占地用保守矩形 SAT 检查，识别 7 对不可同时放置的候选港口；不是相邻港口实景或全地图验收。基本 GLB 结构检查与 `pnpm lint` 通过，未运行完整 Khronos 校验器。

工具为本地 Blender Python 替代＋**可用的 Computer Use**；完成基线和 1 轮修正，截图保留会话。指令/路径检查、上述视觉评审与 GLB 技术校验完成；**Blender MCP 闭环、Electron 配置组装、动态数字/换色、整盘性能及 Windows/macOS 打包未验证**。最终审美待用户确认。海面无动态波纹，数字牌在样板中保持空白。

复现脚本：`scripts/assets/create_map_base.py`，使用 Blender 后台执行 `-- --work-dir <项目外新临时目录> --mode build`；审美通过后执行 `export`、`composition`，`preview` 可重建源文件组合样板。样板不作为单体模型归档，保留脚本即可重建；当前六地块画面是实际可拆对象，不是合并网格。

## 强盗位置：全部保留并通过净空复核

本轮逐一读取六类 `.blend` 和独立回导的 `.glb`，共 12 份资产：

- 全部存在 `anchor_robber`：Blender `(0.70,-0.83,0)`；GLB Y-up `(0.70,0,0.83)`。约定圆柱净空半径 `0.34`、高度 `1.15`。
- 全部存在独立的 `anchor_number`，与强盗分开；沙漠也保留可选数字挂点，但不固化数字。
- 六类地块的源文件与 GLB：双挂点位置、净空、中心地面支撑和边沿预留带全部通过（`scripts/assets/audit_tile_anchors.py`，12/12）。检测包含地形三角面跨界，不只检查树木和装饰。
- **森林已修正（2026-10-15）**：压平双挂点附近地面并平滑过渡，树木、材质、挂点坐标和面数不变。完成一轮修正，Computer Use 检查棋盘视角、近景、侧面、数字与强盗共存、拼接及 GLB 回导；本轮未验证 Electron。

强盗与数字底座均已独立交付，通过挂点组合，不嵌入地块 GLB。六地块使用同一变换挂载复核通过，不需要逐地块偏移；数字内容的运行时生成尚待实现。

## 待建模顺序

基础地图所需模型已具备；优先实现配置驱动的桌面端装配，不必继续扩充模型数量。后续建模按需安排。

| 顺序 | 模块 / 建议资产标识 | 核心约束与验收 |
| --- | --- | --- |
| 1 | 可复用装饰与主题变体（按需） | 树木/石料等已有内嵌网格，但未做独立资产库；仅在需要复用、换肤或实例化时拆分，不把每个细节拆成文件 |
| 2 | 独立路口补片、海浪/岸线装饰（按需） | 非基础拼接必需；明确观看距离与性能需求后再做，不侵占建筑和港口接口 |

海面可使用已交付 GLB 或渲染端平面；地图布局、插槽、高亮和建造提示属于组合/渲染能力，不列为“缺失模型”。骰子、资源牌与扩展棋子待玩法/表现方案明确后再排期。

## 归档维护

- 仅维护上述固定路径；历史使用 Git 或项目外恢复副本，不重建 `v01/` 等目录。
- 评审日志/截图留会话或临时目录；不提交 `previews/`、`reviews/`、`.blend1`、`.DS_Store`、`__pycache__`。
- 保存前确认 Blender 使用上述固定源文件路径，避免从临时评审文件或旧路径保存、重建版本目录。
