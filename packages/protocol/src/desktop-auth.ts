import { z } from "zod";

export const GOOGLE_SIGN_IN_CHANNEL = "auth:google-sign-in";
export const googleSignInRequestSchema = z.tuple([]);
export const googleOAuthCredentialsSchema = z.object({
  clientId: z.string().min(1),
  clientSecret: z.string().optional(),
});
export const googleOAuthCallbackSchema = z.object({
  state: z.string(),
  code: z.string().min(1).optional(),
  error: z.string().min(1).optional(),
});
export const googleIdentitySchema = z.object({
  sub: z.string().min(1).max(255),
  nonce: z.string().min(1),
});
export const googleSignInResultSchema = z.discriminatedUnion("ok", [
  z.object({ ok: z.literal(true), googleId: z.string().min(1).max(255) }),
  z.object({ ok: z.literal(false), message: z.string().min(1) }),
]);

export type GoogleSignInResult = z.infer<typeof googleSignInResultSchema>;
export type GoogleOAuthCredentials = z.infer<typeof googleOAuthCredentialsSchema>;
export type DesktopApi = {
  /** 通过系统浏览器确认 Google 身份；不创建游戏账号或保存登录会话。 */
  signInWithGoogle: () => Promise<GoogleSignInResult>;
};
