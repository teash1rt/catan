# 项目规范

## 项目目标

构建面向 Windows 和 macOS 的 3D 卡坦岛桌面游戏，支持多人实时联机对战与可配置游戏规则。

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

不要把游戏规则放入渲染组件、Electron 主进程或数据库访问层。

## 本地启动

- 使用 Node.js 24.18.0 和 pnpm 10.34.0。
- 首次在新环境运行项目时，先执行 `./bootstrap.sh` 完成依赖和 Electron 初始化。
- 当前优先完成 Blender 建模和桌面端 3D 场景，执行 `pnpm dev` 仅启动桌面端。
- 服务端脚手架暂时保留，但在登录与匹配阶段开始前不接入默认开发流程。

## 开发规范

- 使用 `pnpm` 管理依赖和运行脚本，不得混用 npm 或 Yarn。
- 每次修改代码后运行 `pnpm lint`，并解决全部校验问题。
- 3D 场景优先复用 GLB 资产；重复树木、建筑等对象应使用实例化方案。
