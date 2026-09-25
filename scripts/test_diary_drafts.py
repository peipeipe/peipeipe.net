"""Run against npm run dev; requires Python Playwright + Chromium.

GitHub requests are mocked. No real credentials, commits, or posts are created.
Screenshots are written to /tmp/diary-drafts-{mobile,desktop}.png.
"""
import base64
import os
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright, expect

files = {}
head = 'head0'
serial = 0
blobs = {}
trees = {}
commits = {}
fail_publish = False

def api(route):
    global head, serial
    request = route.request
    path = urlparse(request.url).path.split('/repos/peipeipe/peipeipe.net')[1]
    method = request.method
    data = request.post_data_json if request.post_data else {}
    def reply(body, status=200):
        route.fulfill(status=status, json=body)
    serial += 1
    sha = f'sha{serial}'
    if path.startswith('/contents/'):
        name = path[len('/contents/'):]
        if method == 'GET':
            if name == 'diary-drafts':
                entries = [dict(name=k.split('/')[-1], path=k, type='file') for k in files if k.startswith('diary-drafts/')]
                return reply(entries) if entries else reply({}, 404)
            return reply(files[name]) if name in files else reply({}, 404)
        if method == 'PUT':
            if (files.get(name) or {}).get('sha') != data.get('sha'):
                return reply({'message': 'conflict'}, 409)
            files[name] = dict(sha=sha, content=data['content'])
            head = sha
            return reply(dict(content=files[name]))
        if method == 'DELETE':
            if (files.get(name) or {}).get('sha') != data.get('sha'):
                return reply({}, 409)
            del files[name]
            head = sha
            return reply({})
    if path == '/git/ref/heads/master': return reply({'object': {'sha': head}})
    if path.startswith('/git/commits/'):
        return reply({'tree': {'sha': 'base-tree'}})
    if path == '/git/blobs':
        blobs[sha] = data['content']
        return reply({'sha': sha})
    if path == '/git/trees':
        trees[sha] = data['tree']
        return reply({'sha': sha})
    if path == '/git/commits':
        commits[sha] = data
        return reply({'sha': sha})
    if path == '/git/refs/heads/master':
        if fail_publish: return reply({'message': 'test failure'}, 500)
        commit = commits[data['sha']]
        if commit['parents'] != [head]: return reply({}, 422)
        for entry in trees[commit['tree']]:
            if entry['sha'] is None: files.pop(entry['path'], None)
            else: files[entry['path']] = dict(sha=entry['sha'], content=blobs[entry['sha']])
        head = data['sha']
        return reply({})
    raise AssertionError((method, path))

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    def device(mobile=False):
        context = browser.new_context(viewport={'width': 390 if mobile else 1280, 'height': 844 if mobile else 960}, is_mobile=mobile, has_touch=mobile)
        context.route('https://api.github.com/**', api)
        context.route('https://cdn.jsdelivr.net/**', lambda r: r.fulfill(body='window.marked={setOptions(){},parse(s){return s}};', content_type='application/javascript'))
        context.route('https://fonts.googleapis.com/**', lambda r: r.fulfill(body='', content_type='text/css'))
        context.add_init_script("localStorage.setItem('diary_post_cfg', JSON.stringify({token:'test-token'}))")
        page = context.new_page()
        page.on('dialog', lambda d: d.accept())
        page.goto(os.environ.get('DIARY_TEST_URL', 'http://127.0.0.1:4321/diary-post/'))
        # The development-only Astro toolbar overlaps the fixed mobile footer.
        page.add_style_tag(content='astro-dev-toolbar { display: none !important; }')
        expect(page.locator('#token-badge')).to_contain_text('設定済み')
        return page
    pc = device()
    pc.locator('#input-date').fill('2026-09-17')
    pc.locator('#input-time').fill('09:30')
    pc.locator('#content').fill('PCで書いた日記。日本語と絵文字📷')
    pc.locator('#btn-save-draft').click()
    expect(pc.locator('#draft-status')).to_contain_text('保存済み')
    draft_path = next(iter(files))
    assert len(files) == 1 and draft_path.startswith('diary-drafts/')
    mobile = device(True)
    mobile.locator('#draft-panel summary').click()
    expect(mobile.locator('#draft-list option')).to_have_count(2)
    mobile.locator('#draft-list').select_option(draft_path)
    mobile.locator('#btn-open-draft').click()
    expect(mobile.locator('#content')).to_have_value('PCで書いた日記。日本語と絵文字📷')
    expect(mobile.locator('#input-date')).to_have_value('2026-09-17')
    expect(mobile.locator('#input-time')).to_have_value('09:30')
    mobile.locator('#content').fill('スマホで加筆📷')
    mobile.locator('#btn-save-draft').click()
    expect(mobile.locator('#draft-status')).to_contain_text('保存済み')
    pc.locator('#content').fill('古いPCから上書き')
    pc.locator('#btn-save-draft').click()
    expect(pc.locator('.toast-msg').last).to_contain_text('競合')
    assert base64.b64decode(files[draft_path]['content']).decode().find('スマホで加筆') >= 0
    pc.locator('#btn-submit').click()
    expect(pc.locator('.toast-msg').last).to_contain_text('別の端末で更新')
    expect(pc.locator('#content')).to_have_value('古いPCから上書き')
    png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=')
    mobile.locator('#file-image').set_input_files({'name':'photo.png','mimeType':'image/png','buffer':png})
    expect(mobile.locator('#image-list img')).to_have_count(1)
    expect(mobile.locator('#btn-submit')).to_be_enabled()
    assert mobile.evaluate('document.documentElement.scrollWidth <= innerWidth')
    for page in (pc, mobile):
        page.locator('.toast').evaluate_all('(toasts) => toasts.forEach(toast => toast.click())')
        expect(page.locator('.toast')).to_have_count(0)
        page.locator('#btn-submit').scroll_into_view_if_needed()
        save_box = page.locator('#btn-save-draft').bounding_box()
        submit_box = page.locator('#btn-submit').bounding_box()
        # The primary button rises 1px on hover.
        assert abs(save_box['y'] - submit_box['y']) <= 2
        assert save_box['x'] + save_box['width'] <= submit_box['x']
    mobile.screenshot(path='/tmp/diary-drafts-mobile.png', full_page=True)
    pc.screenshot(path='/tmp/diary-drafts-desktop.png', full_page=True)
    fail_publish = True
    mobile.locator('#btn-submit').click()
    expect(mobile.locator('.toast-title').last).to_have_text('投稿失敗')
    assert draft_path in files
    expect(mobile.locator('#image-list img')).to_have_count(1)
    fail_publish = False
    mobile.locator('#btn-submit').click()
    expect(mobile.locator('#content')).to_have_value('')
    assert draft_path not in files
    diary = base64.b64decode(files['astro/content/diary/2026-09-17.md']['content']).decode()
    assert '## 09:30' in diary and 'スマホで加筆📷' in diary and '/images/diary/2026-09-17-0930.webp' in diary
    assert 'astro/public/images/diary/2026-09-17-0930.webp' in files
    pc.locator('#btn-submit').click()
    expect(pc.locator('.toast-msg').last).to_contain_text('投稿・削除')
    assert base64.b64decode(files['astro/content/diary/2026-09-17.md']['content']).decode() == diary
    mobile.locator('#content').fill('削除する下書き')
    mobile.locator('#btn-save-draft').click()
    expect(mobile.locator('#draft-status')).to_contain_text('保存済み')
    mobile.locator('#draft-panel summary').click()
    mobile.locator('#btn-delete-draft').click()
    expect(mobile.locator('#draft-status')).to_contain_text('削除しました')
    expect(mobile.locator('#content')).to_have_value('削除する下書き')
    assert not any(k.startswith('diary-drafts/') for k in files)
    mobile.locator('#input-time').fill('23:55')
    mobile.locator('#content').fill('端末内の未保存本文📓')
    saved = mobile.evaluate("JSON.parse(localStorage.getItem('diary-editor-v1'))")
    assert saved['text'] == '端末内の未保存本文📓' and 'token' not in saved
    mobile.reload()
    mobile.add_style_tag(content="astro-dev-toolbar { display: none !important; }")
    expect(mobile.locator('#content')).to_have_value('端末内の未保存本文📓')
    expect(mobile.locator('#input-time')).to_have_value('23:55')
    diary_path = 'astro/content/diary/2026-09-17.md'
    original = diary + '\n## 23:55\n隣の項目はそのまま\n'
    files[diary_path] = dict(sha='edit-base', content=base64.b64encode(original.encode()).decode())
    mobile.locator('summary').filter(has_text='投稿済みの日記を編集').click()
    mobile.locator('#edit-date').fill('2026-09-17')
    mobile.locator('#btn-load-entries').click()
    expect(mobile.locator('#edit-entry option')).to_have_count(3)
    mobile.locator('#edit-entry').select_option('0')
    mobile.locator('#btn-edit-entry').click()
    expect(mobile.locator('#input-date')).to_be_disabled()
    expect(mobile.locator('#btn-yesterday')).to_be_disabled()
    text = mobile.locator('#content').input_value()
    assert '/images/diary/' in text
    mobile.locator('#content').fill(text.replace('スマホで加筆📷', '投稿を修正📷'))
    mobile.reload()
    mobile.add_style_tag(content="astro-dev-toolbar { display: none !important; }")
    expect(mobile.locator('#edit-status')).to_contain_text('投稿を編集中')
    expect(mobile.locator('#submit-label')).to_have_text('変更を保存する')
    mobile.locator('#btn-submit').click()
    expect(mobile.locator('#content')).to_have_value('')
    updated = base64.b64decode(files[diary_path]['content']).decode()
    assert updated.count('## 09:30') == 1 and '投稿を修正📷' in updated
    assert '## 23:55\n隣の項目はそのまま' in updated and '/images/diary/' in updated
    assert mobile.evaluate("localStorage.getItem('diary-editor-v1')") is None
    mobile.locator('summary').filter(has_text='投稿済みの日記を編集').click()
    mobile.locator('#edit-date').fill('2026-09-17')
    mobile.locator('#btn-load-entries').click()
    expect(mobile.locator('#edit-entry option')).to_have_count(3)
    mobile.locator('#edit-entry').select_option('1')
    mobile.locator('#btn-edit-entry').click()
    mobile.locator('#content').fill('競合時も残す本文')
    files[diary_path]['sha'] = 'changed-elsewhere'
    mobile.locator('#btn-submit').click()
    expect(mobile.locator('.toast-msg').last).to_contain_text('別の端末')
    expect(mobile.locator('#content')).to_have_value('競合時も残す本文')
    assert base64.b64decode(files[diary_path]['content']).decode() == updated
    assert mobile.evaluate('document.documentElement.scrollWidth <= innerWidth')
    mobile.locator('.toast').evaluate_all('(toasts) => toasts.forEach(toast => toast.click())')
    expect(mobile.locator('.toast')).to_have_count(0)
    mobile.screenshot(path='/tmp/diary-edit-mobile.png', full_page=True)
    browser.close()
print('PASS: drafts, local recovery, entry editing, conflict protection, photo preservation, mobile layout')
