import { z } from "zod";

export {
  GOOGLE_SIGN_IN_CHANNEL,
  googleOAuthCredentialsSchema,
  googleOAuthCallbackSchema,
  googleIdentitySchema,
  googleSignInRequestSchema,
  googleSignInResultSchema,
} from "./desktop-auth.ts";
export type { DesktopApi, GoogleSignInResult, GoogleOAuthCredentials } from "./desktop-auth.ts";

// 共享 schema 必须兼容 Electron 生产环境禁止 eval 的严格 CSP。
z.config({ jitless: true });

export * from "./map.ts";
export * from "./game.ts";
