# catan

面向 Windows 和 macOS 的 3D 卡坦岛桌面游戏，支持多人实时联机对战与可配置游戏规则。

## 技术栈

- 桌面端：Electron、React、Three.js、React Three Fiber
- 服务端：Node.js、Colyseus
- 数据层：PostgreSQL、Drizzle ORM
- 规则引擎：`game-core`（确定性状态转换，由 `RuleConfig` 驱动）

## 目录结构

| 路径                 | 职责                                                    |
| -------------------- | ------------------------------------------------------- |
| `apps/desktop`       | Electron 主进程、React UI、Three.js 场景                |
| `apps/server`        | 认证接口、Colyseus 房间、数据库访问                     |
| `packages/game-core` | 确定性游戏规则、`RuleConfig`、状态转换                  |
| `packages/protocol`  | 共享命令/状态/事件及 Zod schema                         |
| `assets/`            | Blender 源文件（`.blend`）与导出模型（`.glb`，Git LFS） |
| `docs/`              | 资产规范、架构决策、开发计划                            |

## 环境要求

- Node.js `24.18.0`（见 `.nvmrc`）
- pnpm `10.34.0`

## 快速开始

```bash
./bootstrap.sh        # 首次：安装依赖并初始化 Electron
pnpm dev              # 启动桌面端
```

服务端脚手架暂缓接入默认开发流程（登录与匹配阶段前不启用）。

## 常用命令

| 命令                                | 说明                             |
| ----------------------------------- | -------------------------------- |
| `pnpm dev`                          | 启动桌面端开发                   |
| `pnpm build`                        | 构建全部包                       |
| `pnpm lint`                         | oxlint 校验（`--deny-warnings`） |
| `pnpm format` / `pnpm format:check` | Prettier 格式化 / 校验           |
| `pnpm typecheck`                    | 全仓类型检查                     |
| `pnpm test`                         | 运行全部测试                     |

## 约定

- 服务端是游戏状态唯一权威来源，客户端只提交类型化 `GameCommand`。
- 规则集中在 `game-core`，不在 UI 或 Colyseus 房间硬编码玩法变体。
- 跨包输入在边界完成 Zod 校验，共享协议类型不重复定义。
- 代码风格见 `AGENTS.md`。
