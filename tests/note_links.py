import asyncio, os
from playwright.async_api import async_playwright
from helpers import set_md
# [[タイトル]] links one note to another: Ctrl+click moves there, renaming repoints the links
errors = []
def check(label, got, want=True):
    ok = got == want
    print(('OK  ' if ok else 'NG  ') + label + ('' if ok else '  -> got ' + repr(got) + ' want ' + repr(want)))
    if not ok: errors.append(label)
TITLE = "document.getElementById('title').textContent"
RAWS = "[...document.querySelectorAll('#blocks .block')].map(e=>e._raw)"
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(permissions=['clipboard-read', 'clipboard-write']); pg = await ctx.new_page()
        pg.on("pageerror", lambda e: errors.append('pageerror: ' + str(e)) or print("PAGEERROR", e))
        await pg.goto("file://" + os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "index.html"))); await pg.wait_for_timeout(300)
        await pg.click('[data-choice=browser]')
        async def note(md):
            await pg.click('#newNote'); await pg.wait_for_timeout(50); await set_md(pg, md)
        async def idle():
            await pg.click('#title'); await pg.wait_for_timeout(80)

        await note('# 買い物リスト\n\n- たまご')
        await note('# 今日の予定\n\n[[買い物リスト]] を見る\n[[まだ無いメモ]] はこれから')
        await idle()

        check('an existing note is linked', await pg.evaluate("!!document.querySelector('#blocks .nlink:not(.missing)')"))
        check('a missing one is marked', await pg.evaluate("document.querySelector('#blocks .nlink.missing')?.textContent"), 'まだ無いメモ')
        check('the brackets are gone from the display', await pg.evaluate("document.querySelector('#blocks .nlink').textContent"), '買い物リスト')

        # a plain click edits the line as usual
        await pg.click('#blocks .nlink'); await pg.wait_for_timeout(100)
        check('a plain click still edits the line', await pg.evaluate(TITLE), '今日の予定')
        check('and shows the raw markdown', '[[買い物リスト]]' in (await pg.evaluate(RAWS))[2], True)
        await idle()

        # Ctrl+click moves to the linked note
        await pg.keyboard.down('Control'); await pg.click('#blocks .nlink'); await pg.keyboard.up('Control'); await pg.wait_for_timeout(200)
        check('Ctrl+click opens the linked note', await pg.evaluate(TITLE), '買い物リスト')

        # a missing link does nothing
        await pg.click("#list .item:nth-child(1) .open"); await pg.wait_for_timeout(150)
        await idle()
        await pg.keyboard.down('Control'); await pg.click('#blocks .nlink.missing'); await pg.keyboard.up('Control'); await pg.wait_for_timeout(200)
        check('a missing link goes nowhere', await pg.evaluate(TITLE), '今日の予定')
        check('and no note was created', await pg.evaluate("document.querySelectorAll('#list .item').length"), 4)

        # renaming the target repoints the link
        await pg.click("#list .item:has(.t:text-matches('買い物リスト')) .open"); await pg.wait_for_timeout(150)
        await pg.click('#blocks .block:nth-child(1)'); await pg.keyboard.press('End'); await pg.keyboard.type('2026')
        await idle()
        check('the rename is reported', 'リンクを張り替えました' in await pg.inner_text('#toast'), True)
        await pg.click("#list .item:has(.t:text-matches('今日の予定')) .open"); await pg.wait_for_timeout(150)
        check('the link now names the new title', '[[買い物リスト2026]]' in (await pg.evaluate(RAWS))[2], True)
        check('and still resolves', await pg.evaluate("!!document.querySelector('#blocks .nlink:not(.missing)')"))

        # --- typing [[ offers the other notes' titles
        AC = "[...document.querySelectorAll('#ac .it')].map(b=>b.textContent)"
        RAW = "document.querySelector('#blocks .editing')?._raw ?? null"
        await pg.click('#newNote'); await pg.wait_for_timeout(60)
        await pg.keyboard.type('つづきは [['); await pg.wait_for_timeout(150)
        check('the popup lists notes', '買い物リスト2026' in await pg.evaluate(AC), True)
        check('it leaves out the note being written', '無題のメモ' in await pg.evaluate(AC), False)
        await pg.keyboard.type('今日'); await pg.wait_for_timeout(150)
        check('typing filters the list', await pg.evaluate(AC), ['今日の予定'])
        await pg.keyboard.press('Tab'); await pg.wait_for_timeout(150)
        check('Tab puts the link in', await pg.evaluate(RAW), 'つづきは [[今日の予定]]')
        check('the popup closes', await pg.evaluate("document.getElementById('ac').hidden"), True)
        await pg.keyboard.type(' を見る'); await pg.wait_for_timeout(100)
        check('typing carries on after it', await pg.evaluate(RAW), 'つづきは [[今日の予定]] を見る')
        await pg.keyboard.type(' [[買い'); await pg.wait_for_timeout(150)
        check('the popup comes back', len(await pg.evaluate(AC)) > 0, True)
        await pg.keyboard.press('Escape'); await pg.wait_for_timeout(100)
        check('Esc closes it without inserting', await pg.evaluate("document.getElementById('ac').hidden"), True)
        check('and the text is untouched', any(r.endswith(' [[買い') for r in await pg.evaluate(RAWS)), True)
        await idle()
        # the arrows always move the caret: the list never takes them (in a note of its own)
        LINE = "[...document.querySelectorAll('#blocks .block')].findIndex(b=>b.classList.contains('editing'))"
        await pg.click('#newNote'); await pg.wait_for_timeout(60)
        await pg.keyboard.type('矢印の確認'); await pg.keyboard.press('Enter')
        await pg.keyboard.type('二行目'); await pg.keyboard.press('Enter')
        await pg.keyboard.type('三行目 [['); await pg.wait_for_timeout(150)
        check('the popup is open again', await pg.evaluate("document.getElementById('ac').hidden"), False)
        was = await pg.evaluate(LINE)
        await pg.keyboard.press('ArrowUp'); await pg.wait_for_timeout(150)
        check('↑ moves the caret, not the list', await pg.evaluate(LINE), was - 1)
        check('and the list closes', await pg.evaluate("document.getElementById('ac').hidden"), True)
        await pg.keyboard.press('ArrowDown'); await pg.wait_for_timeout(150)
        check('↓ moves it back', await pg.evaluate(LINE), was)
        await pg.keyboard.press('Shift+ArrowUp'); await pg.wait_for_timeout(120)
        check('Shift+↑ works on the text as usual', await pg.evaluate("getSelection().toString().length > 0 || !!document.querySelector('#blocks .bsel')"), True)
        await pg.keyboard.press('Escape'); await pg.wait_for_timeout(100)
        await idle()
        await idle()

        # --- backlinks
        BACK = "[...document.querySelectorAll('#backlinks a')].map(a=>a.textContent)"
        await pg.click('#list .item .t:text-is("今日の予定")'); await pg.wait_for_timeout(200)
        check('the note lists what points at it', await pg.evaluate(BACK), ['つづきは [[今日の予定]] を見る [[買い'])
        await pg.click('#backlinks a'); await pg.wait_for_timeout(200)
        check('clicking one opens it', await pg.evaluate(TITLE), 'つづきは [[今日の予定]] を見る [[買い')
        await pg.click('#list .item .t:text-is("メモ帳へようこそ")'); await pg.wait_for_timeout(200)
        check('a note nobody points at shows nothing', await pg.evaluate("document.getElementById('backlinks').hidden"), True)
        await pg.click('#list .item .t:text-is("買い物リスト2026")'); await pg.wait_for_timeout(200)
        check('a linked note lists its referrer', await pg.evaluate(BACK), ['今日の予定'])

        # links inside code are left alone
        await note('`[[買い物リスト2026]]` はリンクにしない')
        await idle()
        check('code spans are not linked', await pg.evaluate("document.querySelectorAll('#blocks .nlink').length"), 0)
        await b.close()
    print('\nFAILED:', errors if errors else 'none')
asyncio.run(main())
