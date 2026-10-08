import { readFile, writeFile, mkdir, readdir, unlink } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';
import { INBOX, RECEIPTS, MAX_SUBMISSION_BYTES, validateSubmission, buildSubmissionContent } from '../astro/src/lib/diary-submission.mjs';
import { replaceDiarySection } from '../astro/src/lib/diary-edit.mjs';
import { assertDraftUnchanged } from '../astro/src/lib/diary-drafts.mjs';

async function readOptional(path) {
  try { return await readFile(path); } catch (error) { if (error.code === 'ENOENT') return null; throw error; }
}
function fileInfo(bytes) {
  return bytes === null ? null : {
    content: bytes.toString('utf8'),
    sha: createHash('sha1').update(`blob ${bytes.length}\0`).update(bytes).digest('hex'),
  };
}
async function write(path, data) {
  await mkdir(dirname(path), { recursive: true });
  await writeFile(path, data);
}

export async function processInbox(root) {
  const names = (await readdir(resolve(root, INBOX)).catch(e => { if (e.code === 'ENOENT') return []; throw e; })).sort();
  let count = 0;
  for (const name of names) {
    if (!/^[a-f0-9-]{36}\.json$/.test(name)) continue;
    const inboxPath = resolve(root, INBOX, name);
    const receiptPath = resolve(root, RECEIPTS, name);
    if (await readOptional(receiptPath)) { await unlink(inboxPath); count++; continue; }
    let job;
    let prepared;
    try {
      const bytes = await readFile(inboxPath);
      if (bytes.length > MAX_SUBMISSION_BYTES) throw new Error('投稿データが20MBを超えています');
      job = validateSubmission(JSON.parse(bytes.toString('utf8')));
      if (`${job.id}.json` !== name) throw new Error('投稿IDが一致しません');
      const diaryPath = resolve(root, `astro/content/diary/${job.date}.md`);
      const existing = fileInfo(await readOptional(diaryPath));
      if (job.draft) assertDraftUnchanged(job.draft, fileInfo(await readOptional(resolve(root, job.draft.path))));
      const images = job.images.map((image, index) => ({
        path: `images/diary/${job.date}-${job.time.replace(':', '')}-${job.id}-${index + 1}.${image.ext}`,
        bytes: Buffer.from(image.b64, 'base64'),
      }));
      const built = buildSubmissionContent(existing?.content, job, images.map(image => `/${image.path}`));
      const content = job.editing ? replaceDiarySection(existing, job.editing, built.section) : built.content;
      prepared = { diaryPath, content, images };
    } catch (error) {
      // Filesystem failures are retryable; do not consume the accepted payload.
      if (error.code) throw error;
      // Preserve rejected payloads locally in the browser; a receipt prevents retries from duplicating them.
      await write(receiptPath, JSON.stringify({ id: name.slice(0, -5), status: 'failed', message: error.message }) + '\n');
      await unlink(inboxPath);
      count++;
      continue;
    }
    // I/O failures abort the run. The workflow resets to remote before retrying;
    // content, draft consumption, and receipt are published in one Git commit.
    for (const image of prepared.images) await write(resolve(root, 'astro/public', image.path), image.bytes);
    await write(prepared.diaryPath, prepared.content);
    if (job.draft) await unlink(resolve(root, job.draft.path));
    await write(receiptPath, JSON.stringify({ id: job.id, status: 'saved', date: job.date, time: job.time }) + '\n');
    await unlink(inboxPath);
    count++;
  }
  return count;
}

// Only run --publish in the disposable Actions checkout. Never force-push or
// rebase rendered Markdown: re-read the latest content after a push conflict.
export async function publishInbox(root) {
  const git = (...args) => execFileSync('git', args, { cwd: root, stdio: 'pipe' }).toString().trim();
  for (let attempt = 0; attempt < 5; attempt++) {
    git('fetch', 'origin', 'master');
    git('reset', '--hard', 'origin/master');
    // Remove only generated untracked inbox outputs from an interrupted attempt.
    git('clean', '-fd', '--', 'diary-receipts', 'astro/public/images/diary', 'astro/content/diary');
    const count = await processInbox(root);
    console.log(`Processed ${count} diary submission(s)`);
    if (!count) return;
    git('add', '-A', '--', INBOX, RECEIPTS, 'astro/content/diary', 'astro/public/images/diary');
    // The directory can be absent when no draft has ever been saved.
    if (await readdir(resolve(root, 'diary-drafts')).then(() => true).catch(() => false)) git('add', '-A', '--', 'diary-drafts');
    git('-c', 'user.name=github-actions[bot]', '-c', 'user.email=41898282+github-actions[bot]@users.noreply.github.com', 'commit', '-m', 'Publish accepted diary submissions');
    try { git('push', 'origin', 'HEAD:master'); return; } catch (error) { if (attempt === 4) throw error; }
  }
}
if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  if (process.argv.includes('--publish')) {
    if (process.env.GITHUB_ACTIONS !== 'true') throw new Error('--publish is only supported in a disposable Actions checkout');
    await publishInbox(process.cwd());
  } else console.log(`Processed ${await processInbox(process.cwd())} diary submission(s)`);
}
