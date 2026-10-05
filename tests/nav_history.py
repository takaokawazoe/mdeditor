import asyncio, os
from playwright.async_api import async_playwright
from helpers import set_md
# ← / → walk the notes you have been through (links, the list, backlinks, new notes)
errors = []
def check(label, got, want=True):
    ok = got == want
    print(('OK  ' if ok else 'NG  ') + label + ('' if ok else '  -> got ' + repr(got) + ' want ' + repr(want)))
    if not ok: errors.append(label)
TITLE = "document.getElementById('title').textContent"
BTN = "[document.getElementById('navBack').disabled, document.getElementById('navFwd').disabled]"
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(permissions=['clipboard-read', 'clipboard-write']); pg = await ctx.new_page()
        pg.on("pageerror", lambda e: errors.append('pageerror: ' + str(e)) or print("PAGEERROR", e))
        await pg.goto("file://" + os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "index.html"))); await pg.wait_for_timeout(300)
        await pg.click('[data-choice=browser]')
        async def note(md):
            await pg.click('#newNote'); await pg.wait_for_timeout(50); await set_md(pg, md)
            await pg.click('#title'); await pg.wait_for_timeout(100)

        await note('# 買い物リスト\n\n- たまご')
        await note('# 今日の予定\n\n[[買い物リスト]] を見る')
        check('nothing to go forward to yet', await pg.evaluate(BTN), [False, True])

        # following a link is a step
        await pg.keyboard.down('Control'); await pg.click('#blocks .nlink'); await pg.keyboard.up('Control'); await pg.wait_for_timeout(200)
        check('the link opened the other note', await pg.evaluate(TITLE), '買い物リスト')
        await pg.click('#viewBtn'); await pg.click('#navBack'); await pg.wait_for_timeout(200)
        check('← goes back', await pg.evaluate(TITLE), '今日の予定')
        check('and → lights up', await pg.evaluate(BTN), [False, False])
        await pg.click('#viewBtn'); await pg.click('#navFwd'); await pg.wait_for_timeout(200)
        check('→ goes forward again', await pg.evaluate(TITLE), '買い物リスト')

        # the keys do the same
        await pg.keyboard.press('Alt+ArrowLeft'); await pg.wait_for_timeout(200)
        check('Alt+← goes back', await pg.evaluate(TITLE), '今日の予定')
        await pg.keyboard.press('Alt+ArrowRight'); await pg.wait_for_timeout(200)
        check('Alt+→ goes forward', await pg.evaluate(TITLE), '買い物リスト')

        # opening the same note again is not a step: back still reaches the other note
        await pg.click('#list .item .t:text-is("買い物リスト")'); await pg.wait_for_timeout(200)
        await pg.click('#list .item .t:text-is("買い物リスト")'); await pg.wait_for_timeout(200)
        await pg.click('#viewBtn'); await pg.click('#navBack'); await pg.wait_for_timeout(200)
        check('opening the same note twice is one step', await pg.evaluate(TITLE), '今日の予定')
        await pg.click('#viewBtn'); await pg.click('#navFwd'); await pg.wait_for_timeout(200)

        # going back then somewhere else drops what was ahead
        await pg.click('#viewBtn'); await pg.click('#navBack'); await pg.wait_for_timeout(200)
        await pg.click('#list .item .t:text-is("メモ帳へようこそ")'); await pg.wait_for_timeout(200)
        check('a new step clears the way forward', await pg.evaluate(BTN), [False, True])
        await pg.click('#viewBtn'); await pg.click('#navBack'); await pg.wait_for_timeout(200)
        check('back still works', await pg.evaluate(TITLE), '今日の予定')

        # the line you left is where you come back to
        await pg.click('#list .item .t:text-is("買い物リスト")'); await pg.wait_for_timeout(200)
        await pg.click('#blocks .block:nth-child(3)'); await pg.keyboard.press('End')
        await pg.keyboard.press('Escape'); await pg.wait_for_timeout(100)
        await pg.click('#list .item .t:text-is("今日の予定")'); await pg.wait_for_timeout(200)
        await pg.click('#viewBtn'); await pg.click('#navBack'); await pg.wait_for_timeout(250)
        await pg.keyboard.press('Enter'); await pg.wait_for_timeout(150)
        check('coming back lands on the line you left', await pg.evaluate("document.querySelector('#blocks .editing')?._raw"), '- たまご')

        # a deleted note leaves the history
        await pg.click('#list .item .t:text-is("今日の予定")'); await pg.wait_for_timeout(200)
        await pg.click("#list .item:has(.t:text-is('買い物リスト')) .x"); await pg.wait_for_timeout(150)
        await pg.click('#list .item [data-act=del]'); await pg.wait_for_timeout(250)
        for _ in range(6):
            if await pg.evaluate("document.getElementById('navBack').disabled"): break
            await pg.click('#viewBtn'); await pg.click('#navBack'); await pg.wait_for_timeout(150)
        check('the deleted note never comes back', '買い物リスト' not in await pg.evaluate(TITLE), True)
        check('and the app is still fine', await pg.evaluate("document.querySelectorAll('#blocks .block').length") > 0, True)
        await ctx.close()

        # on a phone only ← is shown
        ctx = await b.new_context(viewport={'width': 390, 'height': 700}, has_touch=True, is_mobile=True); pg = await ctx.new_page()
        await pg.goto("file://" + os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "index.html"))); await pg.wait_for_timeout(300)
        await pg.tap('[data-choice=browser]')
        await pg.tap('#moreBtn'); await pg.wait_for_timeout(150)
        vis = await pg.evaluate("[...document.querySelectorAll('#viewMenu .btn')].filter(b=>b.offsetParent).map(b=>b.id)")
        check('the phone menu carries both arrows', vis, ['navBack', 'navFwd', 'toggleSrc'])
        await b.close()
    print('\nFAILED:', errors if errors else 'none')
asyncio.run(main())
