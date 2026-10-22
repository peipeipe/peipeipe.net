import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { pathToFileURL } from "node:url";
import { validateScreenTime, getScreenTime, screenTimeWindow } from "./screentime.mjs";

const payload = (date = "2026-10-17", minutes = 152.482265720765) => ({ date, device: "iPhone", apps: [{ app: "Chrome", minutes }] });

test("Shortcuts dictionary arrays retain numeric precision and sort apps", () => {
  const record = validateScreenTime({ ...payload(), apps: [{ app: "LINE", minutes: 28 }, ...payload().apps] });
  assert.equal(record.apps[0].app, "Chrome");
  assert.equal(record.totalMinutes, 180.482265720765);
  assert.equal(validateScreenTime({ ...payload(), apps: [] }).totalMinutes, 0);
});

test("reject accidental Shortcuts text conversion, impossible dates and invalid durations", () => {
  for (const invalid of [
    { ...payload(), apps: JSON.stringify(payload().apps) },
    { ...payload(), date: 2026 },
    payload("2026-02-30"), payload("2026-13-01"), payload("../secret"),
    payload("2026-10-17", "152"), payload("2026-10-17", -1),
    payload("2026-10-17", Infinity), payload("2026-10-17", 1441),
    { ...payload(), apps: [...payload().apps, ...payload().apps] },
  ]) assert.throws(() => validateScreenTime(invalid));
});

test("seven-day average uses calendar days and distinguishes missing from zero", () => {
  const records = Array.from({ length: 7 }, (_, index) => validateScreenTime(payload(`2026-10-${11 + index}`, index === 0 ? 0 : 70)));
  const days = screenTimeWindow(records);
  assert.equal(days.length, 30);
  assert.equal(days.at(-1).average, 60);
  assert.equal(days.at(-2).average, null);
  assert.equal(days[0].record, null);
  assert.equal(screenTimeWindow(records.slice(1)).at(-1).average, null);
  assert.deepEqual(screenTimeWindow([]), []);
});

test("daily files replace rather than append and filenames must match the date", () => {
  const directory = mkdtempSync(`${tmpdir()}/screentime-`);
  const url = pathToFileURL(`${directory}/`);
  try {
    writeFileSync(new URL("2026-10-17.json", url), JSON.stringify(payload()));
    assert.equal(getScreenTime(url).length, 1);
    writeFileSync(new URL("2026-10-17.json", url), JSON.stringify(payload("2026-10-17", 42)));
    assert.equal(getScreenTime(url)[0].totalMinutes, 42);
    writeFileSync(new URL("2026-10-16.json", url), JSON.stringify(payload()));
    assert.throws(() => getScreenTime(url), /ファイル名/);
  } finally { rmSync(directory, { recursive: true, force: true }); }
});

test("map apps are excluded from historical totals, app lists and seven-day averages", () => {
  const directory = mkdtempSync(`${tmpdir()}/screentime-maps-`);
  const url = pathToFileURL(`${directory}/`);
  try {
    const mapNames = ["Google Maps", "マップ", "Maps", "Apple Maps", "Google マップ", "Googleマップ", "Yahoo!マップ", "Yahoo! MAP", "Yahoo!カーナビ", "Waze"];
    for (let day = 11; day <= 17; day++) {
      const record = payload(`2026-10-${day}`, 30.5);
      record.apps.push(...mapNames.map((app) => ({ app, minutes: 10 })));
      record.apps.push({ app: " MapMyRun ", minutes: 9.5 });
      writeFileSync(new URL(`${record.date}.json`, url), JSON.stringify(record));
      assert.equal(validateScreenTime(record).totalMinutes, 140);
    }
    const records = getScreenTime(url);
    assert.deepEqual(records[0].apps, [{ app: "Chrome", minutes: 30.5 }, { app: "MapMyRun", minutes: 9.5 }]);
    assert.equal(records[0].totalMinutes, 40);
    assert.equal(screenTimeWindow(records).at(-1).average, 40);
    writeFileSync(new URL("2026-10-17.json", url), JSON.stringify({ ...payload(), apps: [{ app: "  GOOGLE MAPS  ", minutes: 20 }] }));
    const mapsOnly = getScreenTime(url).at(-1);
    assert.deepEqual(mapsOnly.apps, []);
    assert.equal(mapsOnly.totalMinutes, 0);
  } finally { rmSync(directory, { recursive: true, force: true }); }
});
