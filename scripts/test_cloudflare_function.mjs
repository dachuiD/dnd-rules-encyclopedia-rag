import assert from "node:assert/strict";
import { onRequest } from "../functions/api/[[path]].js";

class MemoryKV {
  constructor() {
    this.values = new Map();
    this.expirations = new Map();
  }

  async get(key) {
    return this.values.get(key) ?? null;
  }

  async put(key, value, options = {}) {
    this.values.set(key, value);
    if (options.expirationTtl) {
      this.expirations.set(key, options.expirationTtl);
    }
  }
}

function env(overrides = {}) {
  return {
    BACKEND_ORIGIN: "https://ecs.example",
    RAG_GATEWAY_TOKEN: "internal-token",
    RATE_LIMIT_KV: new MemoryKV(),
    ...overrides,
  };
}

function request(path, options = {}) {
  return new Request(`https://demo.pages.dev${path}`, {
    method: options.method ?? "POST",
    headers: {
      "Content-Type": "application/json",
      "CF-Connecting-IP": options.ip ?? "203.0.113.10",
      ...(options.headers ?? {}),
    },
    body: options.body ?? JSON.stringify({ question: "隐身的人攻击有优势吗？" }),
  });
}

async function call(functionEnv, req, fetchImpl) {
  const previousFetch = globalThis.fetch;
  globalThis.fetch = fetchImpl;
  try {
    return await onRequest({ request: req, env: functionEnv });
  } finally {
    globalThis.fetch = previousFetch;
  }
}

async function testProxyInjectsGatewayToken() {
  let captured;
  const response = await call(env(), request("/api/ask?debug=1"), async (url, init) => {
    captured = { url, init };
    return new Response(JSON.stringify({ answer: "ok" }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  });

  assert.equal(response.status, 200);
  assert.equal(captured.url, "https://ecs.example/api/ask?debug=1");
  assert.equal(captured.init.headers.get("X-RAG-GATEWAY-TOKEN"), "internal-token");
  assert.equal(captured.init.headers.has("cf-connecting-ip"), false);
  assert.equal(response.headers.get("Cache-Control"), "no-store");
}

async function testLongQuestionIsRejectedBeforeBackend() {
  let fetched = false;
  const longQuestion = "一".repeat(501);
  const response = await call(
    env(),
    request("/api/ask", { body: JSON.stringify({ question: longQuestion }) }),
    async () => {
      fetched = true;
      return new Response("{}");
    },
  );

  assert.equal(response.status, 400);
  assert.equal(fetched, false);
}

async function testRateLimitRejectsEleventhMinuteRequest() {
  const functionEnv = env();
  let response = null;
  for (let i = 0; i < 11; i += 1) {
    response = await call(functionEnv, request("/api/ask", { ip: "198.51.100.3" }), async () => {
      return new Response(JSON.stringify({ answer: "ok" }), { status: 200 });
    });
  }

  assert.equal(response.status, 429);
}

async function testMissingConfigReturns503() {
  const response = await call(env({ BACKEND_ORIGIN: "" }), request("/api/ask"), async () => {
    return new Response("{}");
  });

  assert.equal(response.status, 503);
}

async function testBackendFetchFailureReturns502() {
  const response = await call(env(), request("/api/ask"), async () => {
    throw new Error("network unavailable");
  });

  assert.equal(response.status, 502);
}

await testProxyInjectsGatewayToken();
await testLongQuestionIsRejectedBeforeBackend();
await testRateLimitRejectsEleventhMinuteRequest();
await testMissingConfigReturns503();
await testBackendFetchFailureReturns502();

console.log("Cloudflare Function smoke tests passed");
