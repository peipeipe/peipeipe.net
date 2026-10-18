export function validateScreenTime(input) {
  if (!input || typeof input !== "object" || Array.isArray(input)) throw new Error("記録は辞書で指定してください");
  const { date, device, apps } = input;
  if (typeof date !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(date)
    || !Number.isFinite(Date.parse(`${date}T00:00:00Z`))
    || new Date(`${date}T00:00:00Z`).toISOString().slice(0, 10) !== date) {
    throw new Error("date は実在する日付 YYYY-MM-DD にしてください");
  }
  if (typeof device !== "string" || !device.trim() || device.length > 100) throw new Error("device が不正です");
  if (!Array.isArray(apps) || apps.length > 1000) throw new Error("apps はアプリの辞書を含む配列にしてください");
  const names = new Set();
  const normalized = apps.map((entry) => {
    if (!entry || typeof entry.app !== "string" || !entry.app.trim() || entry.app.length > 200) throw new Error("app が不正です");
    const app = entry.app.trim();
    if (names.has(app)) throw new Error(`アプリが重複しています: ${app}`);
    names.add(app);
    if (typeof entry.minutes !== "number" || !Number.isFinite(entry.minutes) || entry.minutes < 0 || entry.minutes > 1440) {
      throw new Error(`minutes は0〜1440の数値にしてください: ${app}`);
    }
    return { app, minutes: entry.minutes };
  }).sort((a, b) => b.minutes - a.minutes || a.app.localeCompare(b.app));
  return { date, device: device.trim(), apps: normalized, totalMinutes: normalized.reduce((sum, app) => sum + app.minutes, 0) };
}

