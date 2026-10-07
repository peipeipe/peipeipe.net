# Reliable diary posting

The editor saves a submission (including converted photos) and clears the editor
in one IndexedDB transaction before sending anything. Tokens are never included
in queue payloads. A single GitHub Contents API PUT creates
`diary-inbox/<uuid>.json` using the existing Contents: write token. Only after
that succeeds does the UI report **受付済み**. Before acceptance, the user must
return to the page to resume sending; mobile background execution is not assumed.

The existing Cloudflare Pages workflow processes the durable inbox in its
`accept-diary` job. It writes Markdown, photos, a small receipt in
`diary-receipts/<uuid>.json`, and deletes the consumed inbox/draft in one commit.
The deploy job builds that exact commit. This is intentional: pushes made with
`GITHUB_TOKEN` do not trigger another push workflow. Only the intake job needs
Contents: write. No new Cloudflare service, secret, or browser token permission
is required. Branch rules must allow this Actions job to push to master.

On a competing push, the processor fetches master and recomputes the change;
it never force-pushes or rebases stale generated Markdown. Duplicate delivery
checks the receipt first. A changed draft or edited diary is rejected, with an
error receipt, instead of overwriting another device's changes. The browser
retains the rejected submission and offers restoration to the editor. For edit
conflicts, re-fetch the entry and apply the preserved text to the latest version.

The browser checks receipts on return, on connection recovery, and every 20
seconds while visible. **保存完了** means the content commit exists, not that
Pages deployment has finished. The UI links to the workflow for deployment
status. An interrupted/failed workflow leaves accepted jobs in GitHub; rerun
`Deploy Astro to Cloudflare Pages` with workflow_dispatch, or use the next site
push, to process them. Never manually delete a receipt when retrying a job.

Queue files are kept outside Astro content/public directories. Their contents
(including photos) remain in Git history just like published diary content;
they are not a private draft store. Payloads are limited to 20 MiB and 30 photos.
Photo filenames include the job ID, preventing same-minute posts from replacing
one another's images. Diary URLs and feed routes are unchanged.

Deploy the workflow, processor, shared modules, and editor together. Do not
publish the editor alone. Existing GitHub drafts remain compatible.

Validation:

```sh
PATH=/home/peipeipe/.local/nodejs/current/bin:$PATH node --test scripts/process-diary-inbox.test.mjs astro/src/lib/diary-edit.test.mjs
# With Astro dev running and Playwright installed:
python scripts/test_diary_drafts.py
cd astro
PATH=/home/peipeipe/.local/nodejs/current/bin:$PATH npm run build
PATH=/home/peipeipe/.local/nodejs/current/bin:$PATH npm run check:legacy-slugs
```

`process-diary-inbox.mjs --publish` is for disposable GitHub Actions checkouts
only: it resets that checkout to origin/master before each attempt. Run processor
unit tests in temporary directories; do not run --publish in a working checkout.
