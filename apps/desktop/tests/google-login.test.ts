import assert from "node:assert/strict";
import test from "node:test";
import { GoogleLoginError, signInWithGoogle } from "../src/main/google-login.ts";

const CLIENT_ID = "desktop-test.apps.googleusercontent.com";

function callbackFor(authorizationUrl: string): URL {
  const authorization = new URL(authorizationUrl);
  const callback = new URL(authorization.searchParams.get("redirect_uri") ?? "");
  callback.searchParams.set("state", authorization.searchParams.get("state") ?? "");
  return callback;
}

void test("缺少 Client ID 时不打开浏览器", async () => {
  await assert.rejects(
    signInWithGoogle({ clientId: "" }, () => {
      assert.fail("不应打开浏览器");
    }),
    /Client ID/,
  );
});

void test("错误 state 和无关路径不消耗授权；取消后释放端口", async () => {
  const cancellation = new AbortController();
  let callback: URL | undefined;
  const login = signInWithGoogle(
    { clientId: CLIENT_ID },
    async (url) => {
      callback = callbackFor(url);
      assert.equal(callback.hostname, "127.0.0.1");
      const wrongState = new URL(callback);
      wrongState.searchParams.set("state", "wrong-state");
      wrongState.searchParams.set("code", "wrong-code");
      assert.equal((await fetch(wrongState)).status, 400);
      assert.equal((await fetch(new URL("/favicon.ico", callback))).status, 404);
      cancellation.abort();
    },
    cancellation.signal,
  );

  await assert.rejects(login, GoogleLoginError);
  assert.ok(callback);
  await assert.rejects(fetch(callback));
});

void test("用户拒绝授权后允许重试，且没有遗留回调监听", async () => {
  for (const error of ["access_denied", "temporarily_unavailable"]) {
    let callback: URL | undefined;
    // oxlint-disable-next-line no-await-in-loop -- 串行确认前一次失败清理后可以重新登录。
    await assert.rejects(
      signInWithGoogle({ clientId: CLIENT_ID }, async (url) => {
        callback = callbackFor(url);
        callback.searchParams.set("error", error);
        const response = await fetch(callback);
        assert.equal(response.status, 200);
      }),
      /授权未完成/,
    );
    assert.ok(callback);
    // oxlint-disable-next-line no-await-in-loop -- 检查本次回调端口已经释放。
    await assert.rejects(fetch(callback));
  }
});

void test("浏览器启动失败时结束登录", async () => {
  await assert.rejects(
    signInWithGoogle({ clientId: CLIENT_ID }, () => {
      return Promise.reject(new Error("Browser unavailable"));
    }),
    /无法打开系统浏览器/,
  );
});
