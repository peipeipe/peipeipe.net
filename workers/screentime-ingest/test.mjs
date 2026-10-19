import test from "node:test";
import assert from "node:assert/strict";
import { Buffer } from "node:buffer";
import { handleRequest } from "./worker.mjs";

const env = { INGEST_KEY: "test-only-key-".repeat(4), GITHUB_TOKEN: "test-only-github" };
const record = { date: "2026-10-17", device: "iPhone", apps: [{ app: "日本語", minutes: 12.345 }] };
function request(body = record, headers = {}, url = "https://example.com/api/screentime") {
  return new Request(url, { method: "POST", headers: { "Content-Type": "application/json", "X-Screen-Time-Key": env.INGEST_KEY, ...headers }, body: typeof body === "string" ? body : JSON.stringify(body) });
}
function sequence(steps) {
  let count = 0;
  return { fetch: async (url, init) => {
    assert.ok(count < steps.length, "unexpected GitHub request");
    assert.ok(url.startsWith("https://api.github.com/repos/peipeipe/peipeipe.net/contents/astro/data/screentime/2026-10-17.json"));
    assert.equal(init.headers.Authorization, `Bearer ${env.GITHUB_TOKEN}`);
    const step = steps[count++];
    step.check?.(url, init);
    return Response.json(step.data || {}, { status: step.status });
  }, done() { assert.equal(count, steps.length); } };
}

test("create only the validated date path and UTF-8 JSON; strip extra fields", async () => {
  const mock = sequence([{ status: 404 }, { status: 201, data: { commit: { sha: "commit1" } }, check(url, init) {
    const body = JSON.parse(init.body);
    assert.equal(body.branch, "master");
    assert.equal(body.sha, undefined);
    assert.deepEqual(JSON.parse(Buffer.from(body.content, "base64").toString()), record);
  } }]);
  const response = await handleRequest(request({ ...record, path: "elsewhere", repo: "other" }), env, mock.fetch);
  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), { ok: true, date: record.date, result: "created", commit: "commit1", site: "not_verified" });
  mock.done();
});

test("same-day update supplies SHA; identical retry makes no commit", async () => {
  const mock = sequence([{ status: 200, data: { type: "file", sha: "old", content: "old" } }, { status: 200, data: { commit: { sha: "new" } }, check(url, init) { assert.equal(JSON.parse(init.body).sha, "old"); } }]);
  assert.equal((await (await handleRequest(request(), env, mock.fetch)).json()).result, "updated");
  mock.done();
  const identical = sequence([{ status: 200, data: { type: "file", sha: "new", content: Buffer.from(`${JSON.stringify(record, null, 2)}\n`).toString("base64") } }]);
  assert.equal((await (await handleRequest(request(), env, identical.fetch)).json()).result, "unchanged");
  identical.done();
});

for (const conflict of [409, 422]) test(`retry conflict ${conflict} with fresh SHA`, async () => {
  const mock = sequence([{ status: 404 }, { status: conflict }, { status: 200, data: { type: "file", sha: "fresh" } }, { status: 200, data: { commit: { sha: "done" } }, check(url, init) { assert.equal(JSON.parse(init.body).sha, "fresh"); } }]);
  assert.equal((await handleRequest(request(), env, mock.fetch)).status, 200);
  mock.done();
});

test("bounded conflict retries", async () => {
  const mock = sequence(Array.from({ length: 3 }, () => [{ status: 404 }, { status: 409 }]).flat());
  assert.equal((await handleRequest(request(), env, mock.fetch)).status, 409);
  mock.done();
});

test("reject authentication, size, malformed input, paths and wrong device before GitHub", async () => {
  const never = () => { assert.fail("must not contact GitHub"); };
  const cases = [
    [request(record, { "X-Screen-Time-Key": "wrong" }), 401],
    [request(record, { "Content-Type": "text/plain" }), 415],
    [request("x".repeat(128 * 1024 + 1)), 413],
    [request(record, { "Content-Length": "200000" }), 413],
    [request("bad json"), 400],
    [request(JSON.stringify(JSON.stringify(record))), 400],
    [request({ ...record, date: "../../bad" }), 400],
    [request({ ...record, date: "2026-02-30" }), 400],
    [request({ ...record, device: "iPad" }), 400],
    [request({ ...record, apps: "[]" }), 400],
    [request({ ...record, apps: [...record.apps, ...record.apps] }), 400],
    [request({ ...record, apps: [{ app: "A", minutes: "1" }] }), 400],
    [request({ ...record, apps: [{ app: "A", minutes: -1 }] }), 400],
    [request({ ...record, apps: [{ app: "A", minutes: 1441 }] }), 400],
    [request(record, {}, "https://example.com/api/screentime?key=secret"), 400],
    [request(record, {}, "https://example.com/api/screentime/other"), 404],
    [new Request("https://example.com/api/screentime"), 405],
  ];
  for (const [input, expected] of cases) assert.equal((await handleRequest(input, env, never)).status, expected);
  assert.equal((await handleRequest(request(), {}, never)).status, 503);
});

test("upstream failure responses never expose upstream secrets or claim success", async () => {
  for (const status of [401, 403, 429, 500]) {
    const mock = sequence([{ status }]);
    const response = await handleRequest(request(), env, mock.fetch);
    assert.equal(response.status, 502);
    assert.deepEqual(await response.json(), { ok: false, error: "github_read_failed" });
  }
  assert.deepEqual(await (await handleRequest(request(JSON.stringify(JSON.stringify(record))), env, () => { assert.fail("no fetch"); })).json(), { ok: false, error: "invalid_record", field: "record" });
  const response = await handleRequest(request(), env, () => { throw new Error(env.GITHUB_TOKEN); });
  assert.equal(response.status, 502);
  assert.equal((await response.text()).includes(env.GITHUB_TOKEN), false);
});

test("authenticated check endpoint reports field without writing", async () => {
  const checkUrl = "https://example.com/api/screentime/check";
  const never = () => { assert.fail("check must not write"); };
  const valid = await handleRequest(request(record, {}, checkUrl), env, async () => Response.json({ type: "file" }));
  assert.deepEqual(await valid.json(), { ok: true, date: record.date, apps: 1, saved: false, github: 200 });
  const invalid = await handleRequest(request(JSON.stringify(JSON.stringify(record)), {}, checkUrl), env, never);
  assert.deepEqual(await invalid.json(), { ok: false, error: "invalid_record", field: "record" });
  const query = await handleRequest(request(record, {}, `${checkUrl}?old=1`), env, never);
  assert.deepEqual(await query.json(), { ok: false, error: "invalid_request", field: "url_query" });
  const unauthenticated = await handleRequest(request(record, { "X-Screen-Time-Key": "bad" }, checkUrl), env, never);
  assert.equal(unauthenticated.status, 401);
});
