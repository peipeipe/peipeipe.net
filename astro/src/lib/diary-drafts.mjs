// Kept outside astro/ so saving a draft does not publish or trigger a site build.
export const DRAFT_DIRECTORY = 'diary-drafts';

export function draftPath(date, time, id) {
  return `${DRAFT_DIRECTORY}/${date}-${time.replace(':', '')}-${id}.json`;
}

export function serializeDraft({ date, time, text }) {
  const draft = { version: 1, date, time, text, updatedAt: new Date().toISOString() };
  parseDraft(JSON.stringify(draft));
  return JSON.stringify(draft, null, 2) + '\n';
}

export function parseDraft(content) {
  const draft = JSON.parse(content);
  if (draft?.version !== 1 || typeof draft.text !== 'string'
    || !/^\d{4}-\d{2}-\d{2}$/.test(draft.date)
    || !/^([01]\d|2[0-3]):[0-5]\d$/.test(draft.time)
    || !Number.isFinite(Date.parse(`${draft.date}T${draft.time}:00+09:00`))) {
    throw new Error('下書きの形式が正しくありません');
  }
  return draft;
}

export function assertDraftUnchanged(draft, current) {
  if (draft && (!current || current.sha !== draft.sha)) {
    throw new Error('この下書きは別の端末で更新または投稿・削除されています。本文をコピーしてから、一覧を更新して開き直してください。');
  }
}
