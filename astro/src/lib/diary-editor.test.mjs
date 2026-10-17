import test from 'node:test';
import assert from 'node:assert/strict';
import { selectEditorRecord, editorTextBackup } from './diary-editor.mjs';

const empty = { date: '2026-10-01', time: '12:34', text: '', images: [] };

test('old empty editors do not restore their date, even with stale fallback text', () => {
  assert.equal(selectEditorRecord(empty, { ...empty, text: 'submitted' }), null);
  assert.equal(selectEditorRecord(null, { version: 1, ...empty }), null);
});

test('unfinished text, photos, drafts and published edits retain their date', () => {
  for (const work of [{ text: 'writing' }, { images: [{ b64: 'photo' }] },
    { draft: { path: 'draft.json', sha: 'abc' } }, { editing: { date: empty.date } }]) {
    const restored = selectEditorRecord({ ...empty, ...work }, null);
    assert.equal(restored.date, empty.date);
    for (const [key, value] of Object.entries(work)) assert.deepEqual(restored[key], value);
  }
});

test('legacy text backup is used when primary storage is absent or invalid', () => {
  const backup = editorTextBackup({ ...empty, text: 'unfinished', images: [{ b64: 'photo' }] });
  assert.equal(backup.version, 1);
  assert.equal('images' in backup, false);
  for (const primary of [null, {}, { ...empty, time: '99:99' }]) {
    assert.equal(selectEditorRecord(primary, backup).text, 'unfinished');
  }
  assert.equal(selectEditorRecord({}, { text: 123 }), null);
});
