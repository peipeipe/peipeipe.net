import { readdirSync, readFileSync } from "node:fs";

import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

const dataDirectory = pathToFileURL(`${resolve("data/screentime")}/`);
const dayMs = 86400000;
// Match app names exactly so unrelated apps containing "map" remain counted.
const excludedApps = new Set([
  "maps", "apple maps", "google maps", "google マップ", "googleマップ",
  "マップ", "yahoo!マップ", "yahoo! map", "yahoo!カーナビ", "waze",
]);

import { validateScreenTime } from "./screentime-schema.mjs";
export { validateScreenTime } from "./screentime-schema.mjs";

export function getScreenTime(directory = dataDirectory) {
  return readdirSync(directory).filter((name) => name.endsWith(".json")).map((name) => {
    try {
      const record = validateScreenTime(JSON.parse(readFileSync(new URL(name, directory), "utf8")));
      if (name !== `${record.date}.json`) throw new Error("ファイル名とdateが一致していません");
      const apps = record.apps.filter(({ app }) => !excludedApps.has(app.toLowerCase()));
      return { ...record, apps, totalMinutes: apps.reduce((sum, app) => sum + app.minutes, 0) };
    } catch (error) {
      throw new Error(`スクリーンタイム ${name}: ${error.message}`);
    }
  }).sort((a, b) => a.date.localeCompare(b.date));
}

export function formatScreenMinutes(minutes) {
  const rounded = Math.round(minutes);
  return rounded >= 60 ? `${Math.floor(rounded / 60)}時間${rounded % 60}分` : `${rounded}分`;
}

// The window ends on the newest recorded day; missing days remain null, never zero.
export function screenTimeWindow(records, count = 30) {
  if (!records.length) return [];
  const byDate = new Map(records.map((record) => [record.date, record]));
  const end = Math.max(...records.map((record) => Date.parse(`${record.date}T00:00:00Z`)));
  return Array.from({ length: count }, (_, index) => {
    const timestamp = end - (count - index - 1) * dayMs;
    const date = new Date(timestamp).toISOString().slice(0, 10);
    const week = Array.from({ length: 7 }, (_, offset) => byDate.get(new Date(timestamp - offset * dayMs).toISOString().slice(0, 10)));
    return {
      date,
      record: byDate.get(date) || null,
      average: week.every(Boolean) ? week.reduce((sum, record) => sum + record.totalMinutes, 0) / 7 : null,
    };
  });
}
