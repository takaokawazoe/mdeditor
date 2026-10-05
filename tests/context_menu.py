import asyncio, os
from playwright.async_api import async_playwright
from helpers import set_md
# right-clicking the list (or 「…」 on a phone) opens a menu for that note, folder or empty space
errors = []
def check(label, got, want=True):
    ok = got == want
    print(('OK  ' if ok else 'NG  ') + label + ('' if ok else '  -> got ' + repr(got) + ' want ' + repr(want)))
    if not ok: errors.append(label)
ITEMS = "[...document.querySelectorAll('#ctxmenu .it')].map(b => b.textContent + (b.disabled ? '(不可)' : ''))"
OPEN = "!document.getElementById('ctxmenu').hidden"
TITLES = "[...document.querySelectorAll('#list .item .t')].map(e=>e.textContent)"
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={'width': 1000, 'height': 560}, permissions=['clipboard-read', 'clipboard-write']); pg = await ctx.new_page()
        pg.on("pageerror", lambda e: errors.append('pageerror: ' + str(e)) or print("PAGEERROR", e))
        await pg.goto("file://" + os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "index.html"))); await pg.wait_for_timeout(300)
        await pg.click('[data-choice=browser]')
        async def note(md):
            await pg.click('#newNote'); await pg.wait_for_timeout(50); await set_md(pg, md)
            await pg.click('#title'); await pg.wait_for_timeout(100)
        async def rclick(sel):
            await pg.click(sel, button='right'); await pg.wait_for_timeout(200)

        await pg.click('#newFolder'); await pg.wait_for_timeout(150)
        await pg.keyboard.type('仕事'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(200)
        await note('# 会議メモ\n\n本文')

        # --- a note
        await rclick('#list .item:has-text("会議メモ")')
        check('the note menu', await pg.evaluate(ITEMS), ['開く', 'ロックする', '.mdで保存', 'このメモを複製', '削除'])
        await pg.keyboard.press('Escape'); await pg.wait_for_timeout(100)
        check('Esc closes it', await pg.evaluate(OPEN), False)

        # duplicate
        await rclick('#list .item:has-text("会議メモ")')
        await pg.click('#ctxmenu .it:text-is("このメモを複製")'); await pg.wait_for_timeout(300)
        titles = await pg.evaluate(TITLES)
        check('the copy is there', titles.count('会議メモ'), 2)
        check('and it is the one being read', await pg.evaluate("document.getElementById('title').textContent"), '会議メモ')
        check('in the same folder', await pg.evaluate("JSON.parse(localStorage.getItem('wysimd.v1')).notes.filter(n=>n.blocks[0]==='# 会議メモ').every(n=>n.folder==='仕事')"), True)

        # lock from the menu, then the menu changes with it
        await rclick('#list .item:has-text("会議メモ")')
        await pg.click('#ctxmenu .it:text-is("ロックする")'); await pg.wait_for_timeout(250)
        await rclick('#list .item:has-text("会議メモ")')
        check('a locked note offers to unlock', (await pg.evaluate(ITEMS))[1], 'ロックを解除')
        check('and cannot be deleted or copied', [(await pg.evaluate(ITEMS))[3], (await pg.evaluate(ITEMS))[4]], ['このメモを複製(不可)', '削除(不可)'])
        await pg.click('#ctxmenu .it:text-is("ロックを解除")'); await pg.wait_for_timeout(250)

        # delete through the menu asks first
        await rclick('#list .item:has-text("会議メモ")')
        await pg.click('#ctxmenu .it:text-is("削除")'); await pg.wait_for_timeout(200)
        check('delete asks for a confirmation', await pg.is_visible('#list .item.confirm'), True)
        await pg.click('#list .item [data-act=del]'); await pg.wait_for_timeout(250)
        check('and then it is gone', (await pg.evaluate(TITLES)).count('会議メモ'), 1)

        # --- a folder
        await rclick('#list .folder')
        check('the folder menu', await pg.evaluate(ITEMS),
              ['ここに新しいメモ', 'ここに新しいフォルダ', '名前を変える', '下の階層をすべて閉じる(不可)', 'フォルダを削除'])
        await pg.click('#ctxmenu .it:text-is("名前を変える")'); await pg.wait_for_timeout(200)
        check('rename starts right away', await pg.is_visible('#list .fedit'), True)
        await pg.keyboard.press('Control+a'); await pg.keyboard.type('業務'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(250)
        check('the folder was renamed', await pg.evaluate("[...document.querySelectorAll('#list .folder .fname')].map(e=>e.textContent)"), ['業務'])

        await rclick('#list .folder')
        await pg.click('#ctxmenu .it:text-is("ここに新しいフォルダ")'); await pg.wait_for_timeout(250)
        await pg.keyboard.type('議事録'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(250)
        check('a folder can be made inside', await pg.evaluate("[...document.querySelectorAll('#list .folder .fname')].map(e=>e.textContent)"), ['業務', '議事録'])
        await rclick('#list .folder:has-text("業務")')
        check('now it can be folded', (await pg.evaluate(ITEMS))[3], '下の階層をすべて閉じる')
        await pg.click('#ctxmenu .it:text-is("下の階層をすべて閉じる")'); await pg.wait_for_timeout(250)
        check('the subfolder is hidden', await pg.evaluate("document.querySelectorAll('#list .folder').length"), 1)

        # --- empty space
        lb = await pg.locator('#list').bounding_box()
        await pg.mouse.click(lb['x'] + 60, lb['y'] + lb['height'] - 15, button='right'); await pg.wait_for_timeout(200)
        check('the menu for empty space', await pg.evaluate(ITEMS), ['新しいメモ', '新しいフォルダ', 'すべてのフォルダを閉じる'])
        await pg.keyboard.press('ArrowDown'); await pg.keyboard.press('ArrowDown'); await pg.wait_for_timeout(80)
        check('the keyboard moves through it', await pg.evaluate("document.querySelector('#ctxmenu .it.on').textContent"), 'すべてのフォルダを閉じる')
        await pg.keyboard.press('Enter'); await pg.wait_for_timeout(250)
        check('Enter runs it', await pg.evaluate("[...document.querySelectorAll('#list .folder')].every(f=>!f.classList.contains('open'))"), True)

        # --- not over the search results
        await pg.fill('#gq', 'メモ'); await pg.wait_for_timeout(250)
        await pg.click('#list .item', button='right'); await pg.wait_for_timeout(200)
        check('no menu while searching', await pg.evaluate(OPEN), False)
        await pg.fill('#gq', ''); await pg.wait_for_timeout(200)
        await ctx.close()

        # --- phones get a 「…」 on every row
        ctx = await b.new_context(viewport={'width': 390, 'height': 700}, has_touch=True, is_mobile=True); pg = await ctx.new_page()
        await pg.goto("file://" + os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "index.html"))); await pg.wait_for_timeout(300)
        await pg.tap('[data-choice=browser]')
        await pg.tap('#menu'); await pg.wait_for_timeout(300)
        check('the row button is shown', await pg.is_visible('#list .item .rowmenu'), True)
        await pg.tap('#list .item .rowmenu'); await pg.wait_for_timeout(250)
        check('tapping it opens the same menu', await pg.evaluate(ITEMS), ['開く', 'ロックする', '.mdで保存', 'このメモを複製', '削除'])
        await b.close()
    print('\nFAILED:', errors if errors else 'none')
asyncio.run(main())
