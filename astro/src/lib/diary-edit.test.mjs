import { test } from 'node:test';
import assert from 'node:assert/strict';
import { diarySections, replaceDiarySection } from './diary-edit.mjs';

const content = '---\ntitle: 日記\n---\n\n## 09:30\n朝📷\n![写真](/photo.webp)\n\n## 09:30\n同じ時刻の別項目\n\n## 23:55\n夜\n';
test('editing preserves metadata, adjacent entries and photos, even with duplicate times', () => {
  const entries = diarySections(content);
  assert.equal(entries.length, 3);
  const result = replaceDiarySection({ sha: 'original', content }, { sha: 'original', index: 1, time: '09:30' }, '\n## 09:30\n修正\n');
  assert.ok(result.startsWith(content.slice(0, entries[1].start)));
  assert.ok(result.endsWith(content.slice(entries[2].start)));
  assert.equal(diarySections(result)[1].text, '修正');
});
test('ignores time headings inside fenced code blocks', () => {
  assert.equal(diarySections('## 12:00\n```md\n## 13:00\n```\n~~~\n## 14:00\n~~~\n## 15:00\n本文').length, 2);
});
test('stale or deleted entries cannot overwrite the latest content', () => {
  const editing = { sha: 'original', index: 0, time: '09:30' };
  assert.throws(() => replaceDiarySection({ sha: 'new', content }, editing, 'replacement'), /変更/);
  assert.throws(() => replaceDiarySection(null, editing, 'replacement'), /変更/);
});
