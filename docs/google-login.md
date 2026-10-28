# Google 登录方案与接入指南

更新：2026-10-28。用户已确认原桌面登录演示可用；演示按钮和 toast 已移除，
保留可直接调用的 Google 身份认证能力。当前不创建游戏账号，不接入 PostgreSQL
或 Colyseus，也不持久化登录会话。

## 已实现方案

1. 渲染进程调用 preload 暴露的 `window.catan.signInWithGoogle()`。
2. 主进程打开系统默认浏览器，发起 Google 桌面应用授权，只请求 `openid`。
3. Google 将授权码返回到本机 `127.0.0.1` 的随机端口，路径为 `/oauth2/callback`。
4. 主进程检查本次请求的 `state`，通过授权码和 PKCE 换取 ID Token。
5. Google 官方库验证 Token 签名、签发者、目标 Client ID 和有效期；再检查 `nonce`。
6. preload 返回验证过的 Google 用户 ID，即 ID Token 的 `sub`。成功后应用回到前台。

`sub` 是稳定的 Google 账号标识；Token 是有有效期的凭证，两者用途不同。
Google Token、授权码及客户端凭据不会经 IPC 返回到渲染进程。
Google 登录需要系统浏览器，不应改为在 Electron 的内嵌页面里加载授权页。

## 文件职责

| 文件                                             | 职责                                                       |
| ------------------------------------------------ | ---------------------------------------------------------- |
| `apps/desktop/src/main/google-login.ts`          | 桌面 OAuth、PKCE、回调监听、Token 验证和清理               |
| `apps/desktop/src/main/index.ts`                 | 注册 IPC、按窗口防止重复登录、关闭窗口或退出应用时取消授权 |
| `apps/desktop/src/preload/index.ts`              | 暴露受限调用接口，校验跨进程返回值                         |
| `packages/protocol/src/desktop-auth.ts`          | 共享请求、结果类型和 Zod schema                            |
| `apps/desktop/src/renderer/src/desktop-api.d.ts` | 渲染进程 `window.catan` 类型声明                           |
| `apps/desktop/tests/google-login.test.ts`        | 回调、安全验证及错误处理测试                               |

## 配置接入

在 Google Cloud 的 Google Auth Platform 中配置应用同意界面，创建 **Desktop app**
类型的 OAuth 客户端。开发和正式环境宜使用各自的客户端配置。

本地配置文件为 `apps/desktop/.env.local`；新环境参考同目录的 `.env.example`：

```dotenv
MAIN_VITE_GOOGLE_CLIENT_ID=你的桌面应用客户端编号
MAIN_VITE_GOOGLE_CLIENT_SECRET=下载的桌面应用凭据中的客户端密钥
```

当前开发环境已配置，无需再依赖下载目录中的原始 JSON 文件。`.env.local` 已被
Git 忽略，不应提交真实凭据。Client ID 必填，Client Secret 按所创建的桌面凭据配置。

electron-vite 将这两个变量编译进主进程；修改后需重启 `pnpm dev` 或重新执行
`pnpm build`。桌面应用属于公开客户端，分发后无法向最终用户保密其客户端凭据，
因此本流程使用 PKCE、state 和 nonce，不依赖客户端密钥保密。不要在此处配置
服务端签名密钥、数据库密码等服务端秘密。

## 后续页面如何调用

在 Electron 渲染进程直接调用，无需重新实现 OAuth、手动操作 IPC 或引入 Google SDK。
按钮、等待状态和成功后的页面跳转由实际页面负责。

```ts
async function confirmGoogleIdentity(): Promise<void> {
  try {
    const result = await window.catan.signInWithGoogle();
    if (!result.ok) {
      console.error(result.message);
      return;
    }

    // 将 ID 交给本地界面状态；此处尚未建立服务端游戏会话。
    console.log(result.googleId);
  } catch {
    // 桥接不可用或 IPC 数据不符合协议时，页面需要允许用户重试。
    console.error("暂时无法发起 Google 登录，请重试。");
  }
}
```

返回值类型 `GoogleSignInResult` 统一从 `@catan/protocol` 导入：

| 结果         | 返回内容                                               |
| ------------ | ------------------------------------------------------ |
| 成功         | `{ ok: true, googleId: string }`                       |
| 已处理的失败 | `{ ok: false, message: string }`，可直接展示 `message` |

仅在主进程内部需要复用时，调用 `signInWithGoogle(config, openBrowser, cancellation?)`，
其返回 `Promise<string>`，失败则抛出异常。`GoogleLoginError` 的信息可以展示；SDK
原始异常可能携带敏感请求信息，应像现有 IPC 处理器一样转换成通用错误。

## 使用须知

- 当前地图界面没有登录入口或自动登录。调用接口才会打开浏览器，也不会自动连接服务端。
- 同一窗口同时只允许一次登录；不同窗口各自管理请求，但系统浏览器的 Google 账号
  会话仍由浏览器共享。每次授权都会显示账号选择，调试时可以选择不同账号。
- 登录整体最多等待两分钟，单次网络请求配置十五秒超时。直接关闭浏览器标签页不会
  发送取消回调，需要等超时；明确拒绝授权会立即结束，并允许重试。
- 授权成功、失败、取消或超时都会清理回调监听。关闭所属窗口或退出应用也会取消请求。
- 每次调用都重新授权，不保存 Token、不自动续期，也没有游戏会话的登出功能。
- **本地拿到 `googleId` 不等于已登录游戏服务端。** 后续服务端必须独立验证 Google
  凭证，再关联内部 `userId` 并签发游戏自己的会话；不能信任客户端单独上报的 `sub`。
- 不以邮箱、昵称或 Token 字符串作为稳定账号标识。绑定已有用户名账号时，需要确认
  玩家拥有该账号，避免误合并或生成两份战绩。

## 测试与验收

`pnpm test` 覆盖缺少配置、回调归属校验、取消后端口释放、拒绝授权后重试和
浏览器启动失败。这些测试只访问本机回调端口，不调用 Google，也不需要外部测试工具。
自动化测试当前不覆盖 Google 换码接口或 ID Token 签名验证的端到端流程。

真实授权回归可在 Electron 渲染进程的 DevTools 控制台执行：

```js
await window.catan.signInWithGoogle();
```

在系统浏览器授权后，应返回 `{ ok: true, googleId: "…" }`；同一账号重复登录的
`googleId` 应一致。拒绝授权、关闭标签页后等待超时或网络失败时，应返回
`{ ok: false, message: "…" }`，且下一次调用可以重试。

原按钮和 toast 的界面验收是历史记录，后续页面应围绕上述接口重新验收自身交互。

## 待定事项

| 事项         | 后续需要确定                                                                                |
| ------------ | ------------------------------------------------------------------------------------------- |
| 正式账号接入 | 服务端如何接收、验证 Google 凭证，并签发游戏会话；当前 IPC 仅返回 `sub`，需配合正式方案调整 |
| 账号关联     | Google 身份与内部 `userId` 的表结构、唯一约束、首次登录和主动绑定流程                       |
| 会话管理     | 是否记住登录、凭证保存位置、续期、退出登录和多设备策略                                      |
| 产品入口     | 首页或账号页的入口、等待和错误展示、是否提供显式取消按钮                                    |
| 发布回归     | 正式 Google 应用的发布配置，以及 Windows/macOS 打包后的浏览器回调验证                       |

参考：[Google 桌面授权](https://developers.google.com/identity/protocols/oauth2/native-app)、
[Google ID Token 验证](https://developers.google.com/identity/gsi/web/guides/verify-google-id-token)。
