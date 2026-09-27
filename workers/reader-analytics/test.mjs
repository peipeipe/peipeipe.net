import assert from 'node:assert/strict';
import { test } from 'node:test';
import { DatabaseSync } from 'node:sqlite';
import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';
import worker, { dayKey, pagePath, visitorId, report, scheduled, enqueue, flushNotifications } from './worker.mjs';

function database() {
  const sqlite = new DatabaseSync(':memory:');
  sqlite.exec(readFileSync(new URL('./migrations/0001_analytics.sql', import.meta.url), 'utf8'));
  return {
    prepare(sql) {
      const statement = sqlite.prepare(sql);
      let args = [];
      const wrapper = {
        bind(...values) { args = values; return wrapper; },
        async run() { return { success: true, meta: statement.run(...args) }; },
        async all() { return { results: statement.all(...args) }; },
        async first() { return statement.get(...args) || null; },
      };
      return wrapper;
    },
    async batch(statements) { return Promise.all(statements.map(s => s.all())); },
  };
}
function environment() {
  return { DB: database(), SITE_ORIGIN: 'https://www.peipeipe.net', IP_HASH_SECRET: 's'.repeat(32), ADMIN_TOKEN: 'a'.repeat(32), HEAVY_PV: '100', HEAVY_PAGES: '30', PV_MODE: 'daily' };
}
function request(path = '/diary/2026-09-27/', headers = {}, ip = '192.0.2.1') {
  const req = new Request('https://www.peipeipe.net/_analytics/collect', {
    method: 'POST', headers: { Origin: 'https://www.peipeipe.net', 'CF-Connecting-IP': ip, ...headers },
    body: JSON.stringify({ path }),
  });
  req.cf = { country: 'JP', region: 'Tokyo', city: 'Tokyo' };
  return req;
}

test('JST date boundary and daily keyed pseudonyms', async () => {
  assert.equal(dayKey(Date.parse('2026-09-26T14:59:59Z')), '2026-09-26');
  assert.equal(dayKey(Date.parse('2026-09-26T15:00:00Z')), '2026-09-27');
  const id = await visitorId('192.0.2.1', '2026-09-27', 'secret');
  assert.equal(id, await visitorId('192.0.2.1', '2026-09-27', 'secret'));
  assert.notEqual(id, await visitorId('192.0.2.1', '2026-09-28', 'secret'));
  assert.notEqual(id, await visitorId('192.0.2.1', '2026-09-27', 'other'));
});

test('strips query and fragment; rejects external and private paths', () => {
  const origin = 'https://www.peipeipe.net';
  assert.equal(pagePath('/search/?q=secret#private', origin), '/search/');
  for (const path of ['//evil.test', '/\\evil.test', '/diary-post/', '/%64iary-reader/', '/_analytics/report', '/404.html', '/%0a']) assert.equal(pagePath(path, origin), null);
});

test('counts repeated PV separately from distinct pages and sources; reports are private', async () => {
  const env = environment();
  for (const path of ['/diary/a/', '/diary/a/', '/blog/b/']) assert.equal((await worker.fetch(request(path), env)).status, 204);
  await worker.fetch(request('/blog/b/', {}, '192.0.2.2'), env);
  const data = await report(env, dayKey());
  assert.equal(data.pv, 4);
  assert.equal(data.uniquePages, 2);
  assert.equal(data.sources, 2);
  assert.equal(data.visitors[0].pages, 2);
  assert.equal(data.visitors[0].pv, 3);
  assert.ok(!JSON.stringify(data).includes('192.0.2'));
  assert.equal((await worker.fetch(new Request(env.SITE_ORIGIN + '/_analytics/report'), env)).status, 401);
  const response = await worker.fetch(new Request(env.SITE_ORIGIN + '/_analytics/report', { headers: { Authorization: `Bearer ${env.ADMIN_TOKEN}` } }), env);
  assert.equal(response.status, 200);
  assert.equal((await response.json()).pv, 4);
});

test('rejects invalid traffic and honors privacy opt-outs without writing', async () => {
  const env = environment();
  assert.equal((await worker.fetch(request('/', { Origin: 'https://evil.test' }), env)).status, 403);
  assert.equal((await worker.fetch(request('/', { DNT: '1' }), env)).status, 204);
  assert.equal((await worker.fetch(request('/', { 'Sec-GPC': '1' }), env)).status, 204);
  assert.equal((await worker.fetch(request('/diary-post/'), env)).status, 400);
  const large = new Request(env.SITE_ORIGIN + '/_analytics/collect', { method: 'POST', headers: { Origin: env.SITE_ORIGIN, 'CF-Connecting-IP': '192.0.2.1' }, body: 'x'.repeat(3000) });
  assert.equal((await worker.fetch(large, env)).status, 400);
  assert.equal((await report(env, dayKey())).pv, 0);
});

test('heavy alert fires once, daily summary at JST 09:00, and retention cleans old rows', async () => {
  const env = environment();
  env.HEAVY_PAGES = '2';
  env.DISCORD_WEBHOOK_URL = 'https://discord.com/api/webhooks/test/test';
  await worker.fetch(request('/a'), env);
  await worker.fetch(request('/b'), env);
  const previousFetch = globalThis.fetch;
  const messages = [];
  globalThis.fetch = async (url, options) => { messages.push(JSON.parse(options.body)); return new Response(null, { status: 204 }); };
  try {
    const morning = Date.parse(dayKey() + 'T00:00:00Z');
    await scheduled(env, morning - 60000);
    assert.equal(messages.length, 1);
    assert.match(messages[0].content, /大量閲覧/);
    await scheduled(env, morning);
    await scheduled(env, morning + 300000);
    assert.equal(messages.length, 2);
    assert.match(messages[1].content, /昨日の閲覧レポート/);
    assert.deepEqual(messages[1].allowed_mentions, { parse: [] });
    await env.DB.prepare('UPDATE views SET day=?').bind('2000-01-01').run();
    await scheduled(env, morning + 600000);
    assert.equal((await env.DB.prepare('SELECT COUNT(*) AS n FROM views').first()).n, 0);
  } finally { globalThis.fetch = previousFetch; }
});

test('outbox retries 429 and does not resend acknowledged notifications', async () => {
  const env = environment();
  env.DISCORD_WEBHOOK_URL = 'https://discord.com/api/webhooks/test/test';
  await enqueue(env, 'test', dayKey(), 'PV');
  await enqueue(env, 'test', dayKey(), 'duplicate');
  let calls = 0;
  await flushNotifications(env, 1000, async () => { calls++; return new Response(null, { status: 429, headers: { 'Retry-After': '300' } }); });
  await flushNotifications(env, 2000, async () => { throw new Error('too early'); });
  assert.equal(calls, 1);
  await flushNotifications(env, 302000, async () => { calls++; return new Response(null, { status: 204 }); });
  await flushNotifications(env, 600000, async () => { calls++; return new Response(null, { status: 204 }); });
  assert.equal(calls, 2);
});

test('each-PV option adds one outbox entry per view while preserving counts', async () => {
  const env = environment();
  env.PV_MODE = 'each';
  env.DISCORD_WEBHOOK_URL = 'https://discord.com/api/webhooks/test/test';
  await worker.fetch(request('/a'), env);
  await worker.fetch(request('/a'), env);
  assert.equal((await env.DB.prepare('SELECT COUNT(*) AS n FROM notifications').first()).n, 2);
  assert.equal((await report(env, dayKey())).pv, 2);
});

test('browser waits until visible, sends once, omits private URL data and skips preview', () => {
  const script = readFileSync(new URL('../../astro/public/reader-analytics.js', import.meta.url), 'utf8');
  const calls = [];
  const events = {};
  const context = {
    location: { origin: 'https://www.peipeipe.net', pathname: '/diary/a/', search: '?private=secret' }, navigator: {},
    document: { visibilityState: 'hidden', addEventListener: (name, fn) => { events[name] = fn; } },
    fetch: (url, options) => { calls.push({ url, ...options }); return Promise.resolve(); },
  };
  runInNewContext(script, context);
  assert.equal(calls.length, 0);
  context.document.visibilityState = 'visible';
  events.visibilitychange(); events.visibilitychange();
  assert.equal(calls.length, 1);
  assert.deepEqual(JSON.parse(calls[0].body), { path: '/diary/a/' });
  assert.equal(calls[0].referrerPolicy, 'no-referrer');
  assert.equal(calls[0].credentials, 'omit');
  context.location.origin = 'https://preview.pages.dev';
  runInNewContext(script, context);
  assert.equal(calls.length, 1);
});
