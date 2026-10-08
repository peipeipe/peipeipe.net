import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, readFile, writeFile, readdir, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { createHash, randomUUID } from 'node:crypto';
import { processInbox } from './process-diary-inbox.mjs';

const blobSha = text => createHash('sha1').update(`blob ${Buffer.byteLength(text)}\0`).update(text).digest('hex');
async function fixture(t) {
  const root = await mkdtemp(join(tmpdir(), 'diary-inbox-'));
  t.after(() => rm(root, { recursive: true, force: true }));
  const write = async (path, value) => { await mkdir(dirname(join(root, path)), { recursive: true }); await writeFile(join(root, path), value); };
  const job = overrides => ({ version: 1, id: randomUUID(), date: '2026-10-07', time: '09:30', text: '日記📷', images: [], ...overrides });
  const enqueue = async value => { await write(`diary-inbox/${value.id}.json`, JSON.stringify(value)); return value; };
  const read = path => readFile(join(root, path), 'utf8');
  return { root, write, job, enqueue, read };
}

test('photo + draft consumption + receipt; duplicate delivery does not append again', async t => {
  const f = await fixture(t);
  const draft = '{"text":"下書き"}';
  await f.write('diary-drafts/example.json', draft);
  const job = await f.enqueue(f.job({ draft: { path: 'diary-drafts/example.json', sha: blobSha(draft) }, images: [{ b64: 'aW1hZ2U=', ext: 'webp' }] }));
  assert.equal(await processInbox(f.root), 1);
  const first = await f.read('astro/content/diary/2026-10-07.md');
  assert.match(first, /日記📷/);
  assert.match(first, new RegExp(job.id));
  assert.equal(JSON.parse(await f.read(`diary-receipts/${job.id}.json`)).status, 'saved');
  assert.equal((await readdir(join(f.root, 'diary-drafts'))).length, 0);
  await f.enqueue(job);
  await processInbox(f.root);
  assert.equal(await f.read('astro/content/diary/2026-10-07.md'), first);
});

test('stale draft is rejected without modifying diary or losing the draft', async t => {
  const f = await fixture(t);
  await f.write('diary-drafts/example.json', 'changed');
  const job = await f.enqueue(f.job({ draft: { path: 'diary-drafts/example.json', sha: blobSha('old') } }));
  await processInbox(f.root);
  assert.equal(JSON.parse(await f.read(`diary-receipts/${job.id}.json`)).status, 'failed');
  assert.equal(await f.read('diary-drafts/example.json'), 'changed');
  await assert.rejects(f.read('astro/content/diary/2026-10-07.md'), { code: 'ENOENT' });
});

test('edit preserves neighbors and existing images, stale edit cannot overwrite', async t => {
  const f = await fixture(t);
  const original = '---\ntitle: test\n---\n\n## 09:30\nold\n\n## 10:30\nneighbor\n';
  const path = 'astro/content/diary/2026-10-07.md';
  await f.write(path, original);
  const editing = { date: '2026-10-07', time: '09:30', index: 0, sha: blobSha(original) };
  await f.enqueue(f.job({ editing, text: '修正\n![写真](/images/diary/old.webp)' }));
  await processInbox(f.root);
  const updated = await f.read(path);
  assert.match(updated, /修正/);
  assert.match(updated, /## 10:30\nneighbor/);
  assert.match(updated, /old.webp/);
  const stale = await f.enqueue(f.job({ editing, text: 'stale' }));
  await processInbox(f.root);
  assert.equal(await f.read(path), updated);
  assert.equal(JSON.parse(await f.read(`diary-receipts/${stale.id}.json`)).status, 'failed');
});

test('same-minute submissions have distinct photos; invalid input cannot escape directories', async t => {
  const f = await fixture(t);
  await f.enqueue(f.job({ images: [{ ext: 'webp', b64: 'YQ==' }] }));
  await f.enqueue(f.job({ images: [{ ext: 'webp', b64: 'Yg==' }] }));
  const invalid = await f.enqueue(f.job({ draft: { path: '../outside.json', sha: 'a'.repeat(40) } }));
  await processInbox(f.root);
  assert.equal((await readdir(join(f.root, 'astro/public/images/diary'))).length, 2);
  assert.equal((await f.read('astro/content/diary/2026-10-07.md')).match(/## 09:30/g).length, 2);
  assert.equal(JSON.parse(await f.read(`diary-receipts/${invalid.id}.json`)).status, 'failed');
});

test('publisher retries a racing push without losing neighboring content or duplicating submission', async t => {
  const { execFileSync } = await import('node:child_process');
  const { chmod } = await import('node:fs/promises');
  const { publishInbox } = await import('./process-diary-inbox.mjs');
  const f = await fixture(t);
  const remote = join(f.root, 'remote.git');
  const checkout = join(f.root, 'checkout');
  const rival = join(f.root, 'rival');
  const git = (cwd, ...args) => execFileSync('git', args, { cwd, stdio: 'pipe' }).toString().trim();
  git(f.root, 'init', '--bare', remote);
  git(f.root, 'clone', remote, checkout);
  git(checkout, 'config', 'user.name', 'Test');
  git(checkout, 'config', 'user.email', 'test@example.invalid');
  git(checkout, 'checkout', '-b', 'master');
  const job = f.job({ draft: { path: 'diary-drafts/only.json', sha: blobSha('draft') }, images: [{ ext: 'webp', b64: 'YQ==' }] });
  await f.write('checkout/diary-inbox/' + job.id + '.json', JSON.stringify(job));
  await f.write('checkout/diary-drafts/only.json', 'draft');
  await f.write('checkout/astro/content/diary/2026-10-07.md', '---\ntitle: test\n---\n\n## 08:00\noriginal\n');
  git(checkout, 'add', '.');
  git(checkout, 'commit', '-m', 'Initial queued submission');
  git(checkout, 'push', 'origin', 'master');
  git(f.root, '--git-dir=' + remote, 'symbolic-ref', 'HEAD', 'refs/heads/master');
  git(f.root, 'clone', remote, rival);
  git(rival, 'config', 'user.name', 'Rival');
  git(rival, 'config', 'user.email', 'rival@example.invalid');
  // A one-shot local hook creates a competing remote commit just before push.
  const hook = join(checkout, '.git/hooks/pre-push');
  await writeFile(hook, `#!/bin/sh\nrm "$0"\nprintf '\\n## 08:30\\nracing update\\n' >> '${rival}/astro/content/diary/2026-10-07.md'\ngit -C '${rival}' add .\ngit -C '${rival}' commit -m 'Racing update' >/dev/null\ngit -C '${rival}' push origin master >/dev/null 2>&1\n`);
  await chmod(hook, 0o755);
  await publishInbox(checkout);
  const result = git(f.root, '--git-dir=' + remote, 'show', 'master:astro/content/diary/2026-10-07.md');
  assert.match(result, /racing update/);
  assert.equal(result.match(/## 09:30/g).length, 1);
  assert.equal(JSON.parse(git(f.root, '--git-dir=' + remote, 'show', `master:diary-receipts/${job.id}.json`)).status, 'saved');
  const paths = git(f.root, '--git-dir=' + remote, 'ls-tree', '-r', '--name-only', 'master');
  assert.doesNotMatch(paths, /diary-inbox|diary-drafts/);
  await publishInbox(checkout);
  assert.equal(git(f.root, '--git-dir=' + remote, 'show', 'master:astro/content/diary/2026-10-07.md'), result);
});

test('read failure leaves the accepted payload available for retry', async t => {
  const f = await fixture(t);
  const job = await f.enqueue(f.job());
  // A directory in place of a diary file produces an actual filesystem error.
  await mkdir(join(f.root, 'astro/content/diary/2026-10-07.md'), { recursive: true });
  await assert.rejects(processInbox(f.root), { code: 'EISDIR' });
  assert.equal(JSON.parse(await f.read(`diary-inbox/${job.id}.json`)).id, job.id);
  await assert.rejects(f.read(`diary-receipts/${job.id}.json`), { code: 'ENOENT' });
});
