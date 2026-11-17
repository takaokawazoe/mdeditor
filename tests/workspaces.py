import asyncio, os
from playwright.async_api import async_playwright
# the sidebar foot lists places (the browser + folders); only one is on screen at a time
# needs `python3 -m http.server 8123` (the folder picker is emulated with OPFS)
URL = "http://localhost:8123/index.html"
# the picker hands out a different OPFS folder each time it is called
PICK = """window.__pick = 0;
window.showDirectoryPicker = async () => {
  const names = ['仕事', '私物'];
  const n = names[window.__pick++ % names.length];
  const r = await navigator.storage.getDirectory();
  const d = await r.getDirectoryHandle(n, { create: true });
  Object.defineProperty(d, 'name', { value: n });
  return d;
};"""
TITLES = "[...document.querySelectorAll('#list .t')].map(e=>e.textContent.replace('🔒',''))"
PLACES = "[...document.querySelectorAll('#fs .root')].map(e=>e.querySelector('.nm').textContent + (e.classList.contains('on') ? '*' : ''))"
HERE = "document.querySelector('#fs .root.on .nm').textContent"
errors = []
def check(label, got, want=True):
    ok = got == want
    print(('OK  ' if ok else 'NG  ') + label + ('' if ok else '  -> got ' + repr(got) + ' want ' + repr(want)))
    if not ok: errors.append(label)
async def main():
    async with async_playwright() as pw:
        b = await pw.chromium.launch(); ctx = await b.new_context(); pg = await ctx.new_page()
        pg.on("pageerror", lambda e: errors.append('pageerror: ' + str(e)) or print("PAGEERROR", e))
        await pg.add_init_script(PICK)
        await pg.goto(URL); await pg.wait_for_timeout(400)
        await pg.click('[data-choice=browser]'); await pg.wait_for_timeout(200)

        async def note(md):
            await pg.click('#newNote'); await pg.wait_for_timeout(100)
            await pg.keyboard.type(md); await pg.wait_for_timeout(1300)
        async def go(nm):  # click the place by its name
            await pg.click('#fs .root:has-text("%s")' % nm); await pg.wait_for_timeout(1300)

        await note('# ブラウザのメモ')
        check('the browser is where we start', await pg.evaluate(HERE), 'ブラウザ（ローカルストレージ）')

        # --- adding a folder moves into it, and it shows only what is in that folder
        await pg.click('#fs [data-act=add]'); await pg.wait_for_timeout(1400)
        check('the new folder is the place we are in', await pg.evaluate(HERE), '仕事')
        check('both places are listed', await pg.evaluate(PLACES), ['ブラウザ（ローカルストレージ）', '仕事*'])
        check('the browser notes are not dragged along', 'ブラウザのメモ' in await pg.evaluate(TITLES), False)
        await note('# 仕事のメモ')
        check('the note is in the folder', await pg.evaluate(TITLES), ['仕事のメモ'])
        files = await pg.evaluate("(async()=>{const r=await navigator.storage.getDirectory();const d=await r.getDirectoryHandle('仕事');const o=[];for await(const [n] of d.entries())o.push(n);return o})()")
        check('and written as a .md', files, ['仕事のメモ.md'])

        # --- a second folder is its own place again
        await pg.click('#fs [data-act=add]'); await pg.wait_for_timeout(1400)
        check('three places now', await pg.evaluate(PLACES), ['ブラウザ（ローカルストレージ）', '仕事', '私物*'])
        check('the second folder starts empty', await pg.evaluate(TITLES), ['無題のメモ'])
        await note('# 私物のメモ')

        # --- going back shows that place again, with its own notes
        await go('仕事')
        check('back in the first folder', await pg.evaluate(HERE), '仕事')
        check('its note is there and the other one is not', await pg.evaluate(TITLES), ['仕事のメモ'])
        await go('ブラウザ')
        check('the browser still has its own note', await pg.evaluate(TITLES), ['ブラウザのメモ', 'メモ帳へようこそ', 'メモ帳の使い方'])

        # --- search and [[links]] stay inside the place you are in
        await pg.fill('#gq', '仕事のメモ'); await pg.wait_for_timeout(400)
        check('a note in another place is not found', await pg.evaluate("[...document.querySelectorAll('#list .t')].length"), 0)
        await pg.fill('#gq', ''); await pg.wait_for_timeout(300)
        await pg.keyboard.press('Escape')
        await note('# リンク試験\n\n[[仕事のメモ]]')
        await pg.click('#title'); await pg.wait_for_timeout(300)  # leave the line to see it rendered
        check('a link to another place is dead', await pg.evaluate("!!document.querySelector('#blocks .nlink.missing')"), True)

        # --- the place we were in comes back after a reload
        await go('私物')
        await pg.reload(); await pg.wait_for_timeout(1200)
        check('the same place after a reload', await pg.evaluate(HERE), '私物')
        check('with its own note', await pg.evaluate(TITLES), ['私物のメモ'])

        # --- taking a folder off the list keeps the files but drops its notes
        await pg.click('#fs .root:has-text("仕事") .rx'); await pg.wait_for_timeout(200)
        check('it asks first', await pg.inner_text('#fsDlgTitle'), 'フォルダを一覧から外しますか？')
        await pg.click('#fsDlg [data-dlg=ok]'); await pg.wait_for_timeout(600)
        check('the place is gone', await pg.evaluate(PLACES), ['ブラウザ（ローカルストレージ）', '私物*'])
        left = await pg.evaluate("JSON.parse(localStorage.getItem('wysimd.v1')).notes.map(n=>n.blocks[0])")
        check('its notes went with it', '# 仕事のメモ' in left, False)
        files = await pg.evaluate("(async()=>{const r=await navigator.storage.getDirectory();const d=await r.getDirectoryHandle('仕事');const o=[];for await(const [n] of d.entries())o.push(n);return o})()")
        check('but the .md files are untouched', files, ['仕事のメモ.md'])

        # --- and it can be added back, reading the files in again
        await pg.evaluate("window.__pick = 0")
        await pg.click('#fs [data-act=add]'); await pg.wait_for_timeout(1500)
        check('added back', await pg.evaluate(HERE), '仕事')
        check('with the note read from disk', await pg.evaluate(TITLES), ['仕事のメモ'])
        await b.close()
    print('\nFAILED:', errors if errors else 'none')
asyncio.run(main())
