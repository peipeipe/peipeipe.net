import assert from "node:assert/strict";
import test from "node:test";
import { buildDayTimeline } from "../src/lib/reader-timeline.mjs";

test("interleaves diary posts, Strava and check-ins newest first in Tokyo time", () => {
  const records = buildDayTimeline("2026-09-20",
    "<h2>07:45</h2><p>Morning</p><h2>13:11</h2><p>Afternoon</p>",
    [{ start_date: "2026-09-20T02:41:56Z" }],
    [{ last_checkin_at: "2026-09-20T03:00:00+00:00" }]);
  assert.deepEqual(records.map(({ kind, time }) => [kind, time]), [
    ["diary", "13:11"], ["checkin", "12:00"], ["activity", "11:41"], ["diary", "07:45"],
  ]);
});

test("handles UTC date boundaries and midnight without relying on host timezone", () => {
  const records = buildDayTimeline("2026-09-20", "<h2>00:00</h2><p>Midnight</p>",
    [{ start_date: "2026-09-19T15:01:00Z" }]);
  assert.deepEqual(records.map(({ time }) => time), ["00:01", "00:00"]);
});

test("preserves untimed content, nested headings and photos; unknown times go last", () => {
  const body = '<h2 id="time">9:05</h2><p>Text</p><h2>Notes</h2><img src="photo.webp">';
  const records = buildDayTimeline("2026-09-20", `<p>Introduction</p>${body}`, [],
    [{ name: "Missing time" }, { name: "Invalid time", last_checkin_at: "invalid" }]);
  assert.equal(records[0].value, body);
  assert.equal(records[0].time, "09:05");
  assert.equal(records[1].value, "<p>Introduction</p>");
  assert.deepEqual(records.slice(1).map(({ time }) => time), ["時刻不明", "時刻不明", "時刻不明"]);
  assert.equal(records[2].value.name, "Missing time");
});
