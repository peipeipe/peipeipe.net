import { timingSafeEqual } from 'node:crypto';
import { dashboard } from './dashboard.mjs';

const encoder = new TextEncoder();
const DAY = 86400000;
export const dayKey = (time = Date.now()) => new Date(time + 9 * 3600000).toISOString().slice(0, 10);
const threshold = (value, fallback) => /^\d+$/.test(value || '') && Number(value) > 0 ? Number(value) : fallback;
const reply = (body, status = 200, type = 'text/plain; charset=utf-8') => new Response(body, {
  status, headers: { 'Content-Type': type, 'Cache-Control': 'no-store', 'X-Robots-Tag': 'noindex', 'X-Content-Type-Options': 'nosniff' },
});

export function pagePath(value, origin) {
  if (typeof value !== 'string' || value.length > 1000 || !value.startsWith('/') || value.startsWith('//')) return null;
  try {
    const url = new URL(value, origin);
    if (url.origin !== origin) return null;
    const decoded = decodeURIComponent(url.pathname);
    if (/[\\\x00-\x1f\x7f]/.test(decoded) || /^\/(?:_analytics|diary-post|blog-post|diary-reader|cloudflare-preview|404)(?:\/|\.|$)/.test(decoded)) return null;
    return url.pathname;
  } catch { return null; }
}

export async function visitorId(ip, day, secret) {
  const key = await crypto.subtle.importKey('raw', encoder.encode(secret), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  const digest = await crypto.subtle.sign('HMAC', key, encoder.encode(`${day}\n${ip}`));
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, '0')).join('');
}

async function authorized(request, env) {
  if (!env.ADMIN_TOKEN || env.ADMIN_TOKEN.length < 32) return false;
  const supplied = request.headers.get('Authorization') || '';
  const [a, b] = await Promise.all([supplied, `Bearer ${env.ADMIN_TOKEN}`].map((text) => crypto.subtle.digest('SHA-256', encoder.encode(text))));
  return timingSafeEqual(new Uint8Array(a), new Uint8Array(b));
}

async function readSmallJSON(request) {
  if (!request.body) throw new Error('body');
  const reader = request.body.getReader();
  const chunks = [];
  let size = 0;
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    size += value.byteLength;
    if (size > 2048) { await reader.cancel(); throw new Error('body'); }
    chunks.push(value);
  }
  const bytes = new Uint8Array(size);
  let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.length; }
  return JSON.parse(new TextDecoder().decode(bytes));
}

export async function report(env, day) {
  const results = await env.DB.batch([
    env.DB.prepare('SELECT COALESCE(SUM(pv),0) AS pv, COUNT(DISTINCT visitor) AS sources, COUNT(DISTINCT path) AS uniquePages FROM views WHERE day=?').bind(day),
    env.DB.prepare('SELECT visitor, SUM(pv) AS pv, COUNT(*) AS pages, MAX(country) AS country, MAX(region) AS region, MAX(city) AS city FROM views WHERE day=? GROUP BY visitor ORDER BY pv DESC LIMIT 100').bind(day),
    env.DB.prepare('SELECT path, SUM(pv) AS pv, COUNT(*) AS sources FROM views WHERE day=? GROUP BY path ORDER BY pv DESC LIMIT 50').bind(day),
    env.DB.prepare('SELECT COUNT(*) AS count FROM (SELECT visitor FROM views WHERE day=? GROUP BY visitor HAVING SUM(pv)>=? OR COUNT(*)>=?)').bind(day, threshold(env.HEAVY_PV, 100), threshold(env.HEAVY_PAGES, 30)),
  ]);
  return { day, ...results[0].results[0], heavySources: results[3].results[0].count, visitors: results[1].results, pages: results[2].results };
}

export async function enqueue(env, id, day, content) {
  return env.DB.prepare('INSERT OR IGNORE INTO notifications(id,day,content) VALUES(?,?,?)').bind(id, day, content.slice(0, 1900)).run();
}

async function collect(request, env) {
  if (request.headers.get('Origin') !== env.SITE_ORIGIN) return reply('Forbidden', 403);
  if (request.headers.get('DNT') === '1' || request.headers.get('Sec-GPC') === '1') return reply(null, 204);
  if (!env.IP_HASH_SECRET || env.IP_HASH_SECRET.length < 32) return reply('Not configured', 503);
  const ip = request.headers.get('CF-Connecting-IP');
  if (!ip) return reply('Missing edge metadata', 400);
  let data;
  try { data = await readSmallJSON(request); } catch { return reply('Invalid body', 400); }
  const path = pagePath(data?.path, env.SITE_ORIGIN);
  if (!path) return reply('Invalid path', 400);
  const now = Date.now();
  const day = dayKey(now);
  const visitor = await visitorId(ip, day, env.IP_HASH_SECRET);
  const region = ['country', 'region', 'city'].map((key) => String(request.cf?.[key] || '').slice(0, 100));
  await env.DB.prepare(`INSERT INTO views(day,visitor,path,country,region,city,first_seen,last_seen)
    VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(day,visitor,path) DO UPDATE SET pv=pv+1,last_seen=excluded.last_seen`)
    .bind(day, visitor, path, ...region, now, now).run();
  if (env.PV_MODE === 'each' && env.DISCORD_WEBHOOK_URL) {
    await enqueue(env, `pv:${crypto.randomUUID()}`, day,
      `📖 ページ閲覧\n${day} JST\n${path}\nアクセス元: ${visitor.slice(0, 12)}\n推定地域: ${region.filter(Boolean).join(' / ') || '不明'}`);
  }
  return reply(null, 204);
}

export async function flushNotifications(env, now = Date.now(), send = fetch) {
  if (!env.DISCORD_WEBHOOK_URL) return;
  const url = new URL(env.DISCORD_WEBHOOK_URL);
  if (url.protocol !== 'https:' || url.hostname !== 'discord.com' || !url.pathname.startsWith('/api/webhooks/')) throw new Error('Invalid webhook configuration');
  url.searchParams.set('wait', 'true');
  // One batch per invocation, bounded to stay inside Workers Free subrequest limits.
  const { results } = await env.DB.prepare(`UPDATE notifications SET state='sending',lease_until=?,attempts=attempts+1
    WHERE id IN (SELECT id FROM notifications WHERE
      (state='pending' AND next_attempt<=?) OR (state='sending' AND lease_until<?)
      ORDER BY day,id LIMIT 10) RETURNING id,content,attempts`).bind(now + 120000, now, now).all();
  for (let index = 0; index < results.length; index++) {
    const item = results[index];
    let ok = false;
    let rateLimited = false;
    let delay = Math.min(3600000, 60000 * 2 ** Math.min(item.attempts, 6));
    try {
      const response = await send(url.toString(), {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: item.content, allowed_mentions: { parse: [] } }),
        signal: AbortSignal.timeout(10000),
      });
      ok = response.ok;
      rateLimited = response.status === 429;
      if (rateLimited) {
        const retry = Number(response.headers.get('Retry-After'));
        if (Number.isFinite(retry) && retry > 0) delay = Math.max(delay, retry * 1000);
      }
      await response.body?.cancel();
    } catch { /* The outbox retries without logging secrets or payloads. */ }
    await env.DB.prepare('UPDATE notifications SET state=?,lease_until=0,next_attempt=? WHERE id=?')
      .bind(ok ? 'sent' : 'pending', now + delay, item.id).run();
    if (!ok) {
      for (const remaining of results.slice(index + 1)) {
        await env.DB.prepare("UPDATE notifications SET state='pending',lease_until=0,next_attempt=? WHERE id=?")
          .bind(now + delay, remaining.id).run();
      }
      console.warn(JSON.stringify({ event: rateLimited ? 'discord_rate_limited' : 'discord_retry_scheduled' }));
      break;
    }
  }
}

export async function scheduled(env, now = Date.now()) {
  const today = dayKey(now);
  const yesterday = dayKey(now - DAY);
  // Check yesterday too, so visits just before midnight still trigger an alert.
  if (env.DISCORD_WEBHOOK_URL) {
    const { results } = await env.DB.prepare(`SELECT day,visitor,SUM(pv) AS pv,COUNT(*) AS pages,
      MAX(country) AS country,MAX(region) AS region,MAX(city) AS city FROM views
      WHERE day IN (?,?) AND NOT EXISTS (SELECT 1 FROM notifications n WHERE n.id='heavy:'||views.day||':'||views.visitor)
      GROUP BY day,visitor HAVING SUM(pv)>=? OR COUNT(*)>=? LIMIT 10`)
      .bind(today, yesterday, threshold(env.HEAVY_PV, 100), threshold(env.HEAVY_PAGES, 30)).all();
    for (const row of results) {
      await enqueue(env, `heavy:${row.day}:${row.visitor}`, row.day,
        `📚 大量閲覧を検知\n${row.day} JST\n${row.pv} PV / ${row.pages}種類のページ\nアクセス元: ${row.visitor.slice(0, 12)}\n推定地域: ${[row.country, row.region, row.city].filter(Boolean).join(' / ') || '不明'}\nIP由来の集計であり、人数ではありません。`);
    }
    // UTC 00:00 = JST 09:00. Repeated cron invocations retry a missed daily report.
    if (new Date(now + 9 * 3600000).getUTCHours() >= 9) {
      const id = `daily:${yesterday}`;
      if (!await env.DB.prepare('SELECT id FROM notifications WHERE id=?').bind(id).first()) {
        const data = await report(env, yesterday);
        const top = data.pages.slice(0, 5).map((page) => `${page.pv} PV ${page.path.slice(0, 160)}`).join('\n');
        await enqueue(env, id, yesterday,
          `📊 昨日の閲覧レポート（${yesterday} JST）\n${data.pv} PV / ${data.sources}アクセス元 / ${data.uniquePages}種類のページ\n大量閲覧: ${data.heavySources}アクセス元\n人気ページ\n${top || 'なし'}\n詳細: ${env.SITE_ORIGIN}/_analytics/`);
      }
    }
  }
  const cutoff = dayKey(now - 29 * DAY);
  // Bounded cleanup batches; maintenance must not exhaust a single invocation.
  await env.DB.batch([
    env.DB.prepare('DELETE FROM views WHERE (day,visitor,path) IN (SELECT day,visitor,path FROM views WHERE day<? LIMIT 500)').bind(cutoff),
    env.DB.prepare('DELETE FROM notifications WHERE id IN (SELECT id FROM notifications WHERE day<? LIMIT 500)').bind(cutoff),
  ]);
  await flushNotifications(env, now);
}

export default {
  async fetch(request, env) {
    try {
      const url = new URL(request.url);
      if (url.pathname === '/_analytics/collect' && request.method === 'POST') return await collect(request, env);
      if (url.pathname === '/_analytics/' && request.method === 'GET') return reply(dashboard, 200, 'text/html; charset=utf-8');
      if (url.pathname === '/_analytics/report' && request.method === 'GET') {
        if (!await authorized(request, env)) return reply('Unauthorized', 401);
        const day = url.searchParams.get('day') || dayKey();
        if (!/^\d{4}-\d{2}-\d{2}$/.test(day) || day > dayKey() || day < dayKey(Date.now() - 29 * DAY)) return reply('Invalid date', 400);
        const visitor = url.searchParams.get('visitor');
        if (visitor !== null) {
          if (!/^[a-f0-9]{64}$/.test(visitor)) return reply('Invalid visitor', 400);
          const { results } = await env.DB.prepare('SELECT path,pv FROM views WHERE day=? AND visitor=? ORDER BY pv DESC LIMIT 500').bind(day, visitor).all();
          return reply(JSON.stringify({ day, pages: results }), 200, 'application/json');
        }
        return reply(JSON.stringify(await report(env, day)), 200, 'application/json');
      }
      return reply('Not found', 404);
    } catch {
      console.error(JSON.stringify({ event: 'analytics_request_failed' }));
      return reply('Temporarily unavailable', 503);
    }
  },
  async scheduled(controller, env) {
    try { await scheduled(env, controller.scheduledTime); }
    catch { console.error(JSON.stringify({ event: 'analytics_scheduled_failed' })); throw new Error('Analytics scheduled job failed'); }
  },
};
