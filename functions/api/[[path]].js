const MINUTE_LIMIT = 10;
const DAY_LIMIT = 100;
const MAX_QUESTION_CHARS = 500;

export async function onRequest(context) {
  const { request, env } = context;
  if (request.method === "OPTIONS") {
    return new Response(null, { status: 204 });
  }

  if (!env.BACKEND_ORIGIN || !env.RAG_GATEWAY_TOKEN || !env.RATE_LIMIT_KV) {
    return json({ detail: "服务暂未配置完成" }, 503);
  }

  const ip = request.headers.get("CF-Connecting-IP") || "unknown";
  const limited = await rateLimit(env.RATE_LIMIT_KV, ip);
  if (limited) {
    return json({ detail: "请求过于频繁，请稍后再试" }, 429);
  }

  let body = null;
  if (!["GET", "HEAD"].includes(request.method)) {
    body = await request.text();
    const validation = validateBody(request, body);
    if (validation) return validation;
  }

  const target = new URL(request.url);
  const backend = new URL(env.BACKEND_ORIGIN.replace(/\/$/, "") + target.pathname + target.search);
  const headers = new Headers(request.headers);
  headers.set("X-RAG-GATEWAY-TOKEN", env.RAG_GATEWAY_TOKEN);
  headers.delete("host");
  headers.delete("cf-connecting-ip");
  headers.delete("cf-ipcountry");
  headers.delete("cf-ray");

  try {
    const response = await fetch(backend.toString(), {
      method: request.method,
      headers,
      body,
      redirect: "manual",
    });
    const proxiedHeaders = new Headers(response.headers);
    proxiedHeaders.set("Cache-Control", "no-store");
    return new Response(response.body, {
      status: response.status,
      headers: proxiedHeaders,
    });
  } catch (_error) {
    return json({ detail: "后端服务暂时不可用" }, 502);
  }
}

async function rateLimit(kv, ip) {
  const now = Math.floor(Date.now() / 1000);
  const minute = Math.floor(now / 60);
  const day = Math.floor(now / 86400);
  const minuteKey = `rl:${ip}:m:${minute}`;
  const dayKey = `rl:${ip}:d:${day}`;
  const [minuteCount, dayCount] = await Promise.all([increment(kv, minuteKey, 120), increment(kv, dayKey, 90000)]);
  return minuteCount > MINUTE_LIMIT || dayCount > DAY_LIMIT;
}

async function increment(kv, key, ttl) {
  const current = Number((await kv.get(key)) || "0");
  const next = current + 1;
  await kv.put(key, String(next), { expirationTtl: ttl });
  return next;
}

function validateBody(request, body) {
  if (request.method !== "POST" || !new URL(request.url).pathname.endsWith("/api/ask")) {
    return null;
  }
  try {
    const payload = JSON.parse(body || "{}");
    if (typeof payload.question === "string" && payload.question.length > MAX_QUESTION_CHARS) {
      return json({ detail: `问题最长 ${MAX_QUESTION_CHARS} 字` }, 400);
    }
  } catch (_error) {
    return json({ detail: "请求格式不是合法 JSON" }, 400);
  }
  return null;
}

function json(payload, status) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "no-store",
    },
  });
}
