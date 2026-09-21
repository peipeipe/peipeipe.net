const timeFormatter = new Intl.DateTimeFormat("ja-JP", {
  timeZone: "Asia/Tokyo",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});

function timedRecord(kind, value, datetime) {
  const timestamp = Date.parse(datetime || "");
  return {
    kind,
    value,
    timestamp: Number.isFinite(timestamp) ? timestamp : null,
    datetime: Number.isFinite(timestamp) ? datetime : "",
    time: Number.isFinite(timestamp) ? timeFormatter.format(timestamp) : "時刻不明",
  };
}

export function buildDayTimeline(dateId, html, activities = [], checkins = []) {
  const records = [];
  // Only time headings delimit diary posts; keep other headings with their post.
  const headings = [...html.matchAll(/<h2\b[^>]*>\s*([01]?\d|2[0-3]):([0-5]\d)\s*<\/h2>/g)];
  const introduction = html.slice(0, headings[0]?.index ?? html.length);
  if (introduction.trim()) records.push(timedRecord("diary", introduction, ""));
  headings.forEach((heading, index) => {
    const body = html.slice(heading.index, headings[index + 1]?.index ?? html.length);
    records.push(timedRecord("diary", body, `${dateId}T${heading[1].padStart(2, "0")}:${heading[2]}:00+09:00`));
  });
  records.push(...activities.map((activity) => timedRecord("activity", activity, activity.start_date)));
  records.push(...checkins.map((place) => timedRecord("checkin", place, place.last_checkin_at)));
  // Unknown times stay at the end, with original order retained for ties.
  return records.sort((a, b) => (b.timestamp ?? -Infinity) - (a.timestamp ?? -Infinity));
}
