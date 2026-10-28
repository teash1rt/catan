import { createServer } from "node:http";
import { randomBytes, createHash } from "node:crypto";
import { CodeChallengeMethod, OAuth2Client } from "google-auth-library";
import {
  googleOAuthCredentialsSchema,
  googleOAuthCallbackSchema,
  googleIdentitySchema,
} from "@catan/protocol";
import type { GoogleOAuthCredentials } from "@catan/protocol";

// Google 建议桌面应用使用随机 loopback 端口；仅在本机接收回调。
const CALLBACK_HOST = "127.0.0.1";
const CALLBACK_PATH = "/oauth2/callback";
const RANDOM_BYTES = 32;
// 浏览器授权最多等待两分钟，网络请求最多等待十五秒。
const AUTHORIZATION_TIMEOUT_MS = 120_000;
const NETWORK_TIMEOUT_MS = 15_000;

// 仅此类异常允许展示给页面；SDK 异常可能附带敏感请求信息。
export class GoogleLoginError extends Error {}

export async function signInWithGoogle(
  config: GoogleOAuthCredentials,
  openBrowser: (url: string) => Promise<void>,
  cancellation?: AbortSignal,
): Promise<string> {
  const credentials = googleOAuthCredentialsSchema.safeParse(config);
  if (!credentials.success) {
    throw new GoogleLoginError("请先配置 Google 桌面应用 Client ID，然后重新启动应用。");
  }

  const signal = AbortSignal.any([
    AbortSignal.timeout(AUTHORIZATION_TIMEOUT_MS),
    ...(cancellation ? [cancellation] : []),
  ]);
  signal.throwIfAborted();

  const client = new OAuth2Client({
    clientId: credentials.data.clientId,
    ...(credentials.data.clientSecret ? { clientSecret: credentials.data.clientSecret } : {}),
    transporterOptions: { timeout: NETWORK_TIMEOUT_MS, retry: false, signal },
  });
  const state = randomBytes(RANDOM_BYTES).toString("base64url");
  const nonce = randomBytes(RANDOM_BYTES).toString("base64url");
  const verifier = randomBytes(RANDOM_BYTES).toString("base64url");
  const challenge = createHash("sha256").update(verifier).digest("base64url");
  const server = createServer();
  let removeAbortListener: (() => void) | undefined;

  try {
    const code = await new Promise<{ code: string; redirectUri: string }>((resolve, reject) => {
      const abort = (): void => {
        reject(new GoogleLoginError("Google 登录已取消或超时，请重试。"));
      };
      signal.addEventListener("abort", abort, { once: true });
      removeAbortListener = () => signal.removeEventListener("abort", abort);
      server.once("error", reject);
      server.on("request", (request, response) => {
        response.setHeader("Cache-Control", "no-store");
        response.setHeader("Content-Type", "text/plain; charset=utf-8");
        const callbackUrl = new URL(request.url ?? "/", `http://${CALLBACK_HOST}`);
        if (request.method !== "GET" || callbackUrl.pathname !== CALLBACK_PATH) {
          response.writeHead(404).end("页面不存在。");
          return;
        }

        const callback = googleOAuthCallbackSchema.safeParse(
          Object.fromEntries(callbackUrl.searchParams),
        );
        if (!callback.success || callback.data.state !== state) {
          // 无关请求不能消耗本次授权，继续等待匹配 state 的回调。
          response.writeHead(400).end("登录请求不匹配，请从游戏重新发起登录。");
          return;
        }

        if (callback.data.error) {
          response.end("授权未完成，可以关闭此页面并返回游戏。");
          reject(new GoogleLoginError("Google 授权未完成，请重试。"));
          return;
        }

        if (!callback.data.code) {
          response.writeHead(400).end("缺少授权码。");
          reject(new GoogleLoginError("Google 未返回授权码，请重试。"));
          return;
        }

        response.end("已收到 Google 授权，请返回游戏查看登录结果。");
        resolve({ code: callback.data.code, redirectUri });
      });

      let redirectUri = "";
      server.listen(0, CALLBACK_HOST, () => {
        const address = server.address();
        if (address === null || typeof address === "string") {
          reject(new GoogleLoginError("无法启动 Google 登录回调。"));
          return;
        }

        redirectUri = `http://${CALLBACK_HOST}:${address.port}${CALLBACK_PATH}`;
        const url = client.generateAuthUrl({
          redirect_uri: redirectUri,
          scope: ["openid"],
          prompt: "select_account",
          state,
          nonce,
          code_challenge: challenge,
          code_challenge_method: CodeChallengeMethod.S256,
        });
        void openBrowser(url).catch(() => {
          reject(new GoogleLoginError("无法打开系统浏览器，请重试。"));
        });
      });
    });

    // 收到授权码后立即释放本机端口，Token 始终留在主进程内。
    server.close();
    const { tokens } = await client.getToken({
      code: code.code,
      codeVerifier: verifier,
      redirect_uri: code.redirectUri,
    });
    if (!tokens.id_token) {
      throw new GoogleLoginError("Google 未返回身份证明，请重试。");
    }

    const ticket = await client.verifyIdToken({
      idToken: tokens.id_token,
      audience: credentials.data.clientId,
    });
    const payload = googleIdentitySchema.safeParse(ticket.getPayload());
    if (!payload.success || payload.data.nonce !== nonce) {
      throw new GoogleLoginError("Google 身份验证失败，请重新登录。");
    }

    signal.throwIfAborted();
    return payload.data.sub;
  } finally {
    removeAbortListener?.();
    server.close();
    server.closeAllConnections();
  }
}
