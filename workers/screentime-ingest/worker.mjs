import { timingSafeEqual } from "node:crypto";
import { Buffer } from "node:buffer";
import { validateScreenTime } from "../../astro/src/lib/screentime-schema.mjs";

const repository = "https://api.github.com/repos/peipeipe/peipeipe.net";
const branch = "master";
const maxBytes = 128 * 1024;
class HttpError extends Error {
  constructor(status, code) {
    super(code);
    this.status = status;
  }
}

function reply(status, data) {
  return Response.json(data, { status, headers: { "Cache-Control": "no-store" } });
}

// Bound actual stream bytes as well as Content-Length (which may be absent).
async function readBounded(response, limit) {
  if (Number(response.headers.get("content-length")) > limit) throw new HttpError(413, "body_too_large");
  const reader = response.body?.getReader();
  if (!reader) return "";
  let size = 0;
  const chunks = [];
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > limit) {
        await reader.cancel();
        throw new HttpError(413, "body_too_large");
      }
      chunks.push(Buffer.from(value));
    }
  } finally {
    reader.releaseLock();
  }
  return Buffer.concat(chunks).toString("utf8");
}

async function github(env, fetcher, url, body) {
  const response = await fetcher(url, {
    method: body ? "PUT" : "GET",
    headers: {
      Authorization: `Bearer ${env.GITHUB_TOKEN}`,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      "User-Agent": "peipeipe-screentime-ingest",
      ...(body ? { "Content-Type": "application/json" } : {}),
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
    redirect: "error",
    signal: AbortSignal.timeout(10000),
  });
  if (!response.ok) {
    await response.body?.cancel();
    return { status: response.status };
  }
  try {
    return { status: response.status, data: JSON.parse(await readBounded(response, 512 * 1024)) };
  } catch {
    throw new HttpError(502, "github_invalid_response");
  }
}

async function save(record, env, fetcher) {
  const content = Buffer.from(`${JSON.stringify(record, null, 2)}\n`).toString("base64");
  const url = `${repository}/contents/astro/data/screentime/${record.date}.json`;
  for (let attempt = 0; attempt < 3; attempt++) {
    const current = await github(env, fetcher, `${url}?ref=${branch}`);
    if (current.status !== 200 && current.status !== 404) throw new HttpError(502, "github_read_failed");
    if (current.status === 200 && (current.data?.type !== "file" || !current.data.sha)) {
      throw new HttpError(502, "github_invalid_response");
    }
    if (current.data?.content?.replace(/\s/g, "") === content) return { result: "unchanged" };
    const saved = await github(env, fetcher, url, {
      message: `Update screen time for ${record.date}`,
      branch,
      content,
      ...(current.status === 200 ? { sha: current.data.sha } : {}),
    });
    if (saved.status === 200 || saved.status === 201) {
      if (!saved.data?.commit?.sha) throw new HttpError(502, "github_invalid_response");
      return { result: saved.status === 201 ? "created" : "updated", commit: saved.data.commit.sha };
    }
    // Includes concurrent first creation (422) and stale SHA/branch head (409).
    if (![409, 422].includes(saved.status)) throw new HttpError(502, "github_write_failed");
  }
  throw new HttpError(409, "save_conflict_retry");
}

export async function handleRequest(request, env, fetcher = fetch) {
  try {
    const url = new URL(request.url);
    if (url.pathname !== "/api/screentime") throw new HttpError(404, "not_found");
    if (url.search) throw new HttpError(400, "query_not_allowed");
    if (request.method !== "POST") return new Response(null, { status: 405, headers: { Allow: "POST", "Cache-Control": "no-store" } });
    if (!env.INGEST_KEY || env.INGEST_KEY.length < 32 || !env.GITHUB_TOKEN) throw new HttpError(503, "not_configured");
    const supplied = Buffer.from(request.headers.get("X-Screen-Time-Key") || "");
    const expected = Buffer.from(env.INGEST_KEY);
    if (supplied.length !== expected.length || !timingSafeEqual(supplied, expected)) throw new HttpError(401, "unauthorized");
    if (request.headers.get("content-type")?.split(";")[0].trim().toLowerCase() !== "application/json") throw new HttpError(415, "json_required");
    const raw = await readBounded(request, maxBytes);
    let record;
    try {
      const input = JSON.parse(raw);
      const validated = validateScreenTime(input);
      if (validated.device !== "iPhone") throw new Error();
      // Do not persist arbitrary client fields, destinations, or derived totals.
      record = { date: validated.date, device: validated.device, apps: validated.apps };
    } catch {
      throw new HttpError(400, "invalid_record");
    }
    const saved = await save(record, env, fetcher);
    return reply(200, { ok: true, date: record.date, ...saved, site: "not_verified" });
  } catch (error) {
    const status = error instanceof HttpError ? error.status : 502;
    const code = error instanceof HttpError ? error.message : "upstream_unavailable";
    // No request body, URL, app names, headers, or upstream error text in logs.
    if (status >= 500) console.error(JSON.stringify({ event: "screentime_error", code }));
    return reply(status, { ok: false, error: code });
  }
}

export default { fetch(request, env) { return handleRequest(request, env); } };
