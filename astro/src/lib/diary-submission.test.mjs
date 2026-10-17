import test from 'node:test';
import assert from 'node:assert/strict';
import { validateSubmission, MAX_SUBMISSION_BYTES } from './diary-submission.mjs';

const job = { version: 1, id: '12345678-1234-1234-1234-123456789abc',
  date: '2026-10-17', time: '12:00', text: 'test', images: [] };

test('rejects invalid and oversized images before serialization', () => {
  for (const images of [[null], [{ ext: 'png', b64: 123 }],
    [{ ext: 'png', b64: 'A'.repeat(MAX_SUBMISSION_BYTES + 4) }]]) {
    assert.throws(() => validateSubmission({ ...job, images }), /画像|20MB/);
  }
  assert.equal(validateSubmission(job), job);
});
