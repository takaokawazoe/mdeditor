import asyncio, os
from playwright.async_api import async_playwright
# files dropped on the list land in the folder they were dropped on
errors = []
def check(label, got, want=True):
    ok = got == want
    print(('OK  ' if ok else 'NG  ') + label + ('' if ok else '  -> got ' + repr(got) + ' want ' + repr(want)))
    if not ok: errors.append(label)
FOLDERS = "JSON.parse(localStorage.getItem('wysimd.v1')).notes.map(n => (n.blocks[0] || '') + '@' + (n.folder || '-'))"
DROP = """(el, [name, text, kinds]) => {
  const dt = new DataTransfer();
  dt.items.add(new File([text], name, { type: 'text/markdown' }));
  for (const type of kinds) el.dispatchEvent(new DragEvent(type, { dataTransfer: dt, bubbles: true, cancelable: true }));
}"""
async def main():
    async with async_playwright() as pw:
        b = await pw.chromium.launch(); pg = await b.new_page()
        pg.on("pageerror", lambda e: errors.append('pageerror: ' + str(e)) or print("PAGEERROR", e))
        await pg.goto("file://" + os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "index.html"))); await pg.wait_for_timeout(300)
        await pg.click('[data-choice=browser]')
        async def mkfolder(name):
            await pg.click('#newFolder'); await pg.wait_for_timeout(150)
            await pg.keyboard.type(name); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(200)
        async def drop(sel, name, text, kinds=('dragenter', 'dragover', 'drop')):
            await pg.locator(sel).first.evaluate(DROP, [name, text, list(kinds)]); await pg.wait_for_timeout(400)

        await mkfolder('仕事')
        await mkfolder('議事録')  # inside 仕事, since that is the folder just made

        # hovering a folder says where the files would go
        await drop('#list .folder:has-text("仕事")', 'x.md', '# x', ('dragenter', 'dragover'))
        check('the overlay names the folder under the cursor', await pg.inner_text('#drop .where'), 'フォルダ「仕事」に追加します')

        await drop('#list .folder:has-text("仕事")', '落としたメモ.md', '# 落としたメモ\n\n本文')
        check('a file dropped on a folder goes in', '# 落としたメモ@仕事' in await pg.evaluate(FOLDERS), True)
        check('the toast says where it went', '「仕事」に' in await pg.inner_text('#toast'), True)

        # the inner span of a nested folder row works too, and the path is the full one
        await drop('#list .folder:has-text("議事録") .fname', '下の階層.md', '# 下の階層\n\n本文')
        check('a file dropped two levels down', '# 下の階層@仕事/議事録' in await pg.evaluate(FOLDERS), True)

        # a note row means the folder that note is in
        await drop('#list .item:has-text("落としたメモ")', '隣に置く.md', '# 隣に置く\n\n本文')
        check('a file dropped on a note joins that note', '# 隣に置く@仕事' in await pg.evaluate(FOLDERS), True)

        # the folder inside the file name still nests under the folder it was dropped on
        await drop('#list .folder:has-text("仕事")', 'sub/中の.md', '# 中の\n\n本文')
        check('a path inside the file name nests further', '# 中の@仕事/sub' in await pg.evaluate(FOLDERS), True)

        # dropping anywhere else is the old behaviour: the root
        await drop('#editor', '根っこ.md', '# 根っこ\n\n本文')
        check('a file dropped on the page stays at the root', '# 根っこ@-' in await pg.evaluate(FOLDERS), True)
        check('the overlay is back to its usual text', await pg.inner_text('#drop .where'), 'ここに落とすと新しいメモとして追加します')
        check('no folder is left highlighted', await pg.evaluate("document.querySelectorAll('#list .drop-into').length"), 0)
        await b.close()
    print('\nFAILED:', errors if errors else 'none')
asyncio.run(main())
