export const INBOX = 'diary-inbox';
export const RECEIPTS = 'diary-receipts';
export const MAX_SUBMISSION_BYTES = 20 * 1024 * 1024;

export function validateSubmission(job) {
  if (job?.version !== 1 || !/^[a-f0-9-]{36}$/.test(job.id) ||
      typeof job.text !== 'string' || job.text.length > 200000 ||
      !/^\d{4}-\d{2}-\d{2}$/.test(job.date) ||
      !/^([01]\d|2[0-3]):[0-5]\d$/.test(job.time) ||
      !Number.isFinite(Date.parse(`${job.date}T00:00:00Z`)) ||
      new Date(`${job.date}T00:00:00Z`).toISOString().slice(0, 10) !== job.date ||
      !Array.isArray(job.images) || job.images.length > 30 ||
      (!job.text.trim() && !job.images.length)) throw new Error('投稿データの形式が正しくありません');
  for (const image of job.images) {
    if (!['webp', 'jpg', 'jpeg', 'png'].includes(image.ext) || typeof image.b64 !== 'string' ||
        !/^[A-Za-z0-9+/]*={0,2}$/.test(image.b64) || image.b64.length % 4 !== 0 || !image.b64) {
      throw new Error('画像データの形式が正しくありません');
    }
  }
  if (job.draft && (!/^diary-drafts\/[\w-]+\.json$/.test(job.draft.path) || !/^[a-f0-9]{40}$/.test(job.draft.sha))) {
    throw new Error('下書きの参照が正しくありません');
  }
  if (job.editing && (job.editing.date !== job.date || job.editing.time !== job.time ||
      !Number.isInteger(job.editing.index) || job.editing.index < 0 || !/^[a-f0-9]{40}$/.test(job.editing.sha))) {
    throw new Error('編集対象の参照が正しくありません');
  }
  if (new TextEncoder().encode(JSON.stringify(job)).byteLength > MAX_SUBMISSION_BYTES) {
    throw new Error('写真を含む投稿は20MB以内にしてください');
  }
  return job;
}

export function buildSubmissionContent(existing, job, urls) {
  let section = `\n## ${job.time}\n`;
  if (job.text) section += `${job.text}\n`;
  urls.forEach((url, index) => { section += `![${urls.length > 1 ? `投稿画像${index + 1}` : '投稿画像'}](${url})\n`; });
  if (existing) return { section, content: existing.trimEnd() + '\n' + section };
  const [y, m, d] = job.date.split('-');
  const weekday = ['日', '月', '火', '水', '木', '金', '土'][new Date(`${job.date}T00:00:00Z`).getUTCDay()];
  return { section, content: `---\ndate: ${job.date} 00:00:00 +0900\nlayout: diary\ntitle: ${y}年${m}月${d}日(${weekday})\n---\n${section}` };
}
