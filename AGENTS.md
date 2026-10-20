# 项目规范

## 项目目标

构建面向 Windows 和 macOS 的 3D 卡坦岛桌面游戏，支持多人实时联机对战与可配置游戏规则。

## 文档职责

- `README.md` 面向玩家，介绍游戏、当前可用内容、操作方式及发布信息。
- 架构约束、工程约定、开发环境和命令统一维护在 `AGENTS.md`；专题设计与验收记录放在 `docs/`。
- 区分已实现内容与开发目标，不把规划中的功能描述为已经可用。

## 核心技术栈

- 桌面端：Electron、React。
- 3D 渲染：Three.js、React Three Fiber。
- 资产管线：使用 Blender 建模，统一导出 GLB/glTF，由 Three.js 加载；不要在 Electron 中嵌入 Blender。
- 服务端：Node.js、Colyseus。
- 数据层：PostgreSQL、Drizzle ORM。

## 架构约束

- 服务端是游戏状态的唯一权威来源。客户端只能提交类型化 `GameCommand`，不得直接修改 `GameState`。
- 将确定性规则和状态转换集中在 `game-core`。通过 `RuleConfig` 驱动自定义规则，不得在 UI 或 Colyseus 房间中硬编码玩法变体。
- 对每个通过服务端校验的操作，必须在同一个 PostgreSQL 事务中追加有序事件并更新 JSONB 房间快照。
- 使用 Colyseus 内存管理 WebSocket 连接、计时器和运行中的实时状态；客户端通过 Colyseus 接收同步，不得轮询 SQL 获取实时状态。
- PostgreSQL 是服务端唯一的持久化存储。
- 所有跨进程或跨包输入必须在边界处完成 Zod 校验；共享协议类型不得在桌面端和服务端重复定义。

## 目录职责

- `apps/desktop`：Electron 主进程、React UI 和 Three.js 场景。
- `apps/server`：认证接口、Colyseus 房间和数据库访问。
- `packages/game-core`：确定性游戏规则、`RuleConfig` 和状态转换。
- `packages/protocol`：共享命令、状态、事件及其 Zod schema。
- `assets`：Blender 源文件（`.blend`）与运行时模型（`.glb`），使用 Git LFS 管理。
- `docs`：资产规范、专题设计、验收记录和开发计划。

不要把游戏规则放入渲染组件、Electron 主进程或数据库访问层。

## 共享包消费方式

- `@catan/protocol` 和 `@catan/game-core` 通过包名直接导出并消费 TypeScript 源码，不生成 `dist`，不设置预构建步骤或单独的 watch 任务。
- 桌面渲染端由 Vite 编译共享源码并处理热更新；Electron 主进程和 preload 将这两个包纳入打包，不将它们作为运行时外部依赖。
- 测试和服务端使用 Node.js 24 直接运行 TypeScript 源码。共享包只使用可擦除的 TypeScript 语法，相对导入写明 `.ts` 扩展名。
- 类型检查与测试不得依赖已有构建产物；`pnpm build` 当前仅构建桌面应用。

## 本地启动

- 使用 Node.js 24.18.0 和 pnpm 10.34.0。
- 首次在新环境运行项目时，先执行 `./bootstrap.sh` 完成依赖和 Electron 初始化。
- 当前优先完成 Blender 建模和桌面端 3D 场景，执行 `pnpm dev` 仅启动桌面端。
- 服务端脚手架暂时保留，但在登录与匹配阶段开始前不接入默认开发流程。

## 常用命令

| 命令                                | 说明                                     |
| ----------------------------------- | ---------------------------------------- |
| `./bootstrap.sh`                    | 首次安装依赖并初始化 Electron            |
| `pnpm dev`                          | 启动桌面端开发                           |
| `pnpm build`                        | 构建桌面应用                             |
| `pnpm lint` / `pnpm lint:fix`       | oxlint 校验 / 自动修复，警告也会阻止通过 |
| `pnpm format` / `pnpm format:check` | Prettier 格式化 / 校验                   |
| `pnpm typecheck`                    | 全仓类型检查                             |
| `pnpm test`                         | 运行全部测试                             |
| `pnpm --filter @catan/server start` | 使用 Node.js 24 运行服务端源码           |

## 开发规范

- 使用 `pnpm` 管理依赖和运行脚本，不得混用 npm 或 Yarn。
- 每次修改代码后运行 `pnpm lint`，并解决全部校验问题。
- 3D 场景优先复用 GLB 资产；重复树木、建筑等对象应使用实例化方案。

## 代码风格

- 格式化统一由 Prettier 负责（`printWidth: 100`），提交前运行 `pnpm format`；CI 用 `pnpm format:check` 校验。不要手工调整 Prettier 会接管的内容。
- 一行只写一条语句、一条声明；禁止 `const a = 1; const b = 2;` 或 `const x = f(); if (x) g();` 这类同行拼接。
- `if` 即使只有一个语句也必须换行并使用大括号，禁止 `if (cond) return;` 或 `if (cond) throw ...;`。
- 条件表达式混用 `&&` 与 `||` 时，用括号显式分组，不要依赖运算符优先级。
- 逻辑步骤之间用空行分段；一个函数内连续相关的语句归为一组，步骤切换时留空行。
- 魔法数字提取为具名常量（如 `0x6d2b79f5`、`-.00012`、`10000`），常量注释说明来源或含义。
- 变量名表达含义；几何/矩阵的局部短名 `u/v/dt/dx` 可用，但避免 `aa/bb` 这类无意义缩写（改用 `projectionA/projectionB`）。
