import asyncio, os
from playwright.async_api import async_playwright
from helpers import set_md
# the note list is a tree: folders hold notes, and a folder on screen is a folder on disk
# needs `python3 -m http.server 8123` (the folder picker is emulated with OPFS)
URL = "http://localhost:8123/index.html"
PICK = "window.showDirectoryPicker = async () => { const r = await navigator.storage.getDirectory(); return await r.getDirectoryHandle('ftest', {create:true}); };"
LS = """(async () => { const out = [];
  const walk = async (d, p) => { for await (const [n, h] of d.entries()) { const path = p ? p + '/' + n : n;
    if (h.kind === 'directory') await walk(h, path); else out.push(path); } };
  const r = await navigator.storage.getDirectory();
  await walk(await r.getDirectoryHandle('ftest', {create:true}), '');
  return out.sort(); })()"""
ROWS = """[...document.querySelectorAll('#list > *')].map(e => (e.classList.contains('folder') ? 'F' : '.') + (e.style.getPropertyValue('--d') || '0') + ' ' + e.textContent.replace(/[×▾▸✎]/g, '').trim())"""
FOLDERS = "JSON.parse(localStorage.getItem('wysimd.v1')).notes.map(n => (n.blocks[0] || '') + '@' + (n.folder || '-'))"
errors = []
def check(label, got, want=True):
    ok = got == want
    print(('OK  ' if ok else 'NG  ') + label + ('' if ok else '  -> got ' + repr(got) + ' want ' + repr(want)))
    if not ok: errors.append(label)
async def main():
    async with async_playwright() as pw:
        b = await pw.chromium.launch()
        ctx = await b.new_context(permissions=['clipboard-read', 'clipboard-write']); pg = await ctx.new_page()
        pg.on("pageerror", lambda e: errors.append('pageerror: ' + str(e)) or print("PAGEERROR", e))
        await pg.goto("file://" + os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "index.html"))); await pg.wait_for_timeout(300)
        await pg.click('[data-choice=browser]')
        async def mkfolder(name):
            await pg.click('#newFolder'); await pg.wait_for_timeout(150)
            await pg.keyboard.type(name); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(200)
        async def drag(src, dst):
            a = await src.bounding_box(); c = await dst.bounding_box()
            await pg.mouse.move(a['x'] + 40, a['y'] + a['height'] / 2); await pg.mouse.down()
            await pg.mouse.move(a['x'] + 40, a['y'] + a['height'] / 2 + 10, steps=3)
            await pg.mouse.move(c['x'] + 40, c['y'] + c['height'] / 2, steps=8); await pg.wait_for_timeout(100)
            await pg.mouse.up(); await pg.wait_for_timeout(250)

        await pg.click('#newNote'); await pg.wait_for_timeout(50); await set_md(pg, '# 会議メモ\n\n本文')
        await mkfolder('仕事')
        check('the folder shows up', (await pg.evaluate(ROWS))[0], 'F0 仕事0')

        await drag(pg.locator('#list .item:has-text("会議メモ") .open'), pg.locator('#list .folder'))
        check('a note dragged onto it goes in', await pg.evaluate(ROWS), ['F0 仕事1', '.1 会議メモ' + (await pg.evaluate(ROWS))[1][len('.1 会議メモ'):], '.0 メモ帳へようこそ' + (await pg.evaluate(ROWS))[2][len('.0 メモ帳へようこそ'):], (await pg.evaluate(ROWS))[3]])
        check('the note remembers its folder', '# 会議メモ@仕事' in await pg.evaluate(FOLDERS), True)

        # a new note joins the folder of the one being read
        await pg.click('#list .item:has-text("会議メモ") .open'); await pg.wait_for_timeout(150)
        await pg.click('#newNote'); await pg.keyboard.type('# 隣のメモ'); await pg.wait_for_timeout(150)
        await pg.click('#title'); await pg.wait_for_timeout(600)
        check('the new note lands in the same folder', '# 隣のメモ@仕事' in await pg.evaluate(FOLDERS), True)

        # folders nest
        await mkfolder('議事録')
        check('a folder made inside another nests', [r for r in await pg.evaluate(ROWS) if r.startswith('F')], ['F0 仕事2', 'F1 議事録0'])
        await drag(pg.locator('#list .item:has-text("隣のメモ") .open'), pg.locator('#list .folder:has-text("議事録")'))
        check('a note can go two levels down', '# 隣のメモ@仕事/議事録' in await pg.evaluate(FOLDERS), True)

        # collapsing hides what is inside, and it survives a reload
        await pg.click('#list .folder:has-text("仕事") .fname'); await pg.wait_for_timeout(150)
        check('a closed folder hides its notes', len(await pg.evaluate(ROWS)), 3)
        await pg.reload(); await pg.wait_for_timeout(400)
        check('still closed after a reload', len(await pg.evaluate(ROWS)), 3)
        await pg.click('#list .folder:has-text("仕事") .fname'); await pg.wait_for_timeout(150)

        # renaming carries the notes along
        await pg.click('#list .folder:has-text("仕事") .fed'); await pg.wait_for_timeout(150)
        await pg.keyboard.press('Control+a'); await pg.keyboard.type('業務'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(250)
        check('renaming moves everything under it', sorted(x for x in await pg.evaluate(FOLDERS) if '業務' in x),
              ['# 会議メモ@業務', '# 隣のメモ@業務/議事録'])

        # deleting a folder keeps the notes, one level up
        await pg.click('#list .folder:has-text("議事録") .fx'); await pg.wait_for_timeout(150)
        await pg.click('#list .folder [data-fact=del]'); await pg.wait_for_timeout(250)
        check('its notes move up', '# 隣のメモ@業務' in await pg.evaluate(FOLDERS), True)
        check('and it says what happened', 'に移しました' in await pg.inner_text('#toast'), True)

        # illegal characters are dropped from the name
        await pg.click('#list .folder:has-text("業務") .fed'); await pg.wait_for_timeout(150)
        await pg.keyboard.press('Control+a'); await pg.keyboard.type('a/b:c*d'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(250)
        check('the name is cleaned up', [r for r in await pg.evaluate(ROWS) if r.startswith('F')], ['F0 abcd2'])
        await ctx.close()

        # --- the same tree on disk
        ctx = await b.new_context(); pg = await ctx.new_page()
        pg.on("pageerror", lambda e: errors.append('pageerror: ' + str(e)) or print("PAGEERROR", e))
        await pg.add_init_script(PICK)
        await pg.goto(URL); await pg.wait_for_timeout(400)
        await pg.click('[data-choice=folder]'); await pg.wait_for_timeout(1500)
        await pg.click('#newFolder'); await pg.wait_for_timeout(150)
        await pg.keyboard.type('仕事'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(200)
        await pg.click('#newNote'); await pg.keyboard.type('# 議事録'); await pg.wait_for_timeout(1400)
        await drag(pg.locator('#list .item:has-text("議事録") .open'), pg.locator('#list .folder'))
        await pg.wait_for_timeout(1200)
        check('the note is written inside the folder', '仕事/議事録.md' in await pg.evaluate(LS), True)
        check('and not left at the top', '議事録.md' in await pg.evaluate(LS), False)

        # a .md put into a subfolder from outside comes in with its folder
        await pg.evaluate("""(async () => { const r = await navigator.storage.getDirectory();
          const d = await r.getDirectoryHandle('ftest'); const sub = await d.getDirectoryHandle('外部', {create:true});
          const fh = await sub.getFileHandle('外から.md', {create:true}); const w = await fh.createWritable();
          await w.write('# 外から作ったメモ\\n\\n本文'); await w.close(); })()""")
        await pg.click('#fs [data-act=reload]'); await pg.wait_for_timeout(900)
        check('an outside subfolder is picked up', '# 外から作ったメモ@外部' in await pg.evaluate(FOLDERS), True)

        # deleting the note removes the file and the folder it emptied
        await pg.click('#list .item:has-text("議事録") .x'); await pg.wait_for_timeout(100)
        await pg.click('#list .item [data-act=del]'); await pg.wait_for_timeout(1200)
        files = await pg.evaluate(LS)
        check('the file is gone', [f for f in files if f.startswith('仕事/')], [])
        check('the empty folder is cleaned up', [f for f in files if f.startswith('仕事')], [])
        await b.close()
    print('\nFAILED:', errors if errors else 'none')
asyncio.run(main())
