# Blender 脚本保留策略

2026-10-19 清理后保留 16 个 Python 文件，属于**资产制作工具，不是日志，也不是游戏运行时依赖**。用普通 Git 保留，无需 LFS；Electron 发布只使用 GLB，不随游戏运行这些脚本。

| 文件 | 判断 |
| --- | --- |
| `create_forest_tile.py` | 保留：森林生成、导出与预览 |
| `create_brick_tile.py` | 保留：实际是砖/石/麦/羊/沙漠五类地块的共同入口，不能按名字误删 |
| `brick_quarry_geometry.py`、`stone_quarry_geometry.py`、`wheat_field_geometry.py`、`sheep_pasture_geometry.py`、`desert_dune_geometry.py` | 保留：上项按 `--asset-type` 导入的五类几何模块 |
| `create_robber.py`、`create_number_token.py`、`create_vertex_buildings.py`、`create_road.py`、`create_harbor.py`、`create_map_base.py` | 保留：棋子、建筑、海港及基座的生成/导出/组合工具 |
| `audit_tile_anchors.py` | 必须保留：六地块源文件和 GLB 的挂点、实际净空、支撑及边沿回归检查 |
| `review_forest_tile.py` | 保留：源文件、GLB 回导、数字/强盗与相邻地块组合检查，依赖上述 audit |
| `repair_forest_clearance.py` | 可选维护工具：修补已有森林地面、前后验证与临时备份；不是每次建模必跑。生成器 `elevation()` 已包含净空保护，可在确认不再需要修旧源文件后移除 |

结论：**保留 15 个日常管线脚本和 1 个按需修复工具**。旧木构砖厂方案 `brick_workshop_geometry.py` 已移出仓库至本机废纸篓，可恢复；当前入口使用 `brick_quarry_geometry.py`，源码/文档核对未发现旧方案被调用。此判断不代表重新执行了所有 Blender 流程。

## 使用边界

- 正式资产统一为 `assets/<asset-id>/model.blend` 和 `model.glb`；脚本的临时工作目录可保留原有临时命名，验收后按此规范归档，不复制到桌面端源码目录。

- 使用 Blender 自带 Python（含 `bpy`），不是直接执行系统 `python`。开始前读取各脚本的参数。
- `.blend` 是当前可编辑成果；脚本是生成配方，不保证覆盖后续手工调整。不要以“重跑脚本”为由覆盖已验收模型。
- 草稿、渲染、报告写入新建的项目外临时目录；遵循[资产工作流](../../docs/blender-asset-workflow.md)。保留评审脚本不等于保留评审图片。
- 特别注意：森林/五类地块入口的 `--source` 只改变源文件位置，`--export` **仍写正式 GLB 路径**；仅在确认评审通过、备份已有文件后使用，不把它当作无副作用的测试命令。
- 删除旧配方前必须保留可恢复副本（版本控制或项目外备份/废纸篓）；先确认所需版本已提交，未提交的改动仍需单独备份。
