import { pathToFileURL } from "node:url";
import { resolve } from "node:path";
import { getScreenTime, formatScreenMinutes } from "../astro/src/lib/screentime.mjs";

export function previousJapanDate(now = new Date()) {
  return new Date(now.getTime() + 9 * 3600000 - 86400000).toISOString().slice(0, 10);
}

export function notification(records, date) {
  const record = records.find((entry) => entry.date === date);
  const lines = [`📱 スクリーンタイム（${date}）`];
  if (record) {
    lines.push(`合計：${formatScreenMinutes(record.totalMinutes)}（地図・ナビを除く）`);
    for (const { app, minutes } of record.apps.slice(0, 10)) {
      lines.push(`・${app.replace(/[\r\n]/g, " ").slice(0, 80)}：${formatScreenMinutes(minutes)}`);
    }
    if (record.apps.length > 10) lines.push(`ほか${record.apps.length - 10}アプリ`);
  } else {
    lines.push("前日分のデータはまだ登録されていません。");
  }
  lines.push("https://www.peipeipe.net/screentime/");
  return { content: lines.join("\n"), allowed_mentions: { parse: [] } };
}

async function main() {
  const records = getScreenTime(new URL("../astro/data/screentime/", import.meta.url));
  const payload = notification(records, previousJapanDate());
  if (process.argv.includes("--dry-run")) {
    console.log(JSON.stringify(payload, null, 2));
    return;
  }
  const webhook = process.env.DISCORD_WEBHOOK_URL;
  if (!webhook) throw new Error("DISCORD_WEBHOOK_URL is required");
  const url = new URL(webhook);
  url.searchParams.set("wait", "true");
  let response;
  try {
    response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(30000),
    });
  } catch {
    throw new Error("Discord request failed or timed out");
  }
  if (!response.ok) throw new Error(`Discord returned HTTP ${response.status}`);
  console.log(`Sent screen time for ${previousJapanDate()}`);
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
  });
}
