import asyncio, os
from playwright.async_api import async_playwright
# after Esc (nothing open) the keyboard alone gets back into editing: Enter / arrows / Tab
errors = []
def check(label, got, want):
    ok = got == want
    print(('OK  ' if ok else 'NG  ') + label + ('' if ok else '  -> got ' + repr(got) + ' want ' + repr(want)))
    if not ok: errors.append(label)
EDITING = "document.querySelector('#blocks .editing')?._raw ?? null"
IDX = "[...document.querySelectorAll('#blocks .block')].findIndex(b=>b.classList.contains('editing'))"
CARET = """(() => { const el = document.querySelector('#blocks .editing'); if (!el) return -1;
  const s = getSelection(); if (!s.rangeCount) return -1; const r = s.getRangeAt(0);
  const pre = document.createRange(); pre.selectNodeContents(el); pre.setEnd(r.startContainer, r.startOffset); return pre.toString().length; })()"""
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page()
        pg.on("pageerror", lambda e: errors.append('pageerror: ' + str(e)) or print("PAGEERROR", e))
        await pg.goto("file://" + os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "index.html"))); await pg.wait_for_timeout(300)
        await pg.click('[data-choice=browser]')
        await pg.click('#newNote'); await pg.wait_for_timeout(50)
        await pg.keyboard.type('一行目'); await pg.keyboard.press('Enter')
        await pg.keyboard.type('二行目'); await pg.keyboard.press('Enter')
        await pg.keyboard.type('三行目'); await pg.wait_for_timeout(50)

        # stop editing in the middle of the second line
        await pg.click('#blocks .block:nth-child(2)'); await pg.keyboard.press('Home')
        await pg.keyboard.press('ArrowRight'); await pg.keyboard.press('ArrowRight')
        await pg.keyboard.press('Escape'); await pg.wait_for_timeout(80)
        check('Esc leaves editing', await pg.evaluate(EDITING), None)
        check('focus is off the line', await pg.evaluate("document.activeElement.tagName"), 'BODY')

        # Enter picks up exactly where it stopped
        await pg.keyboard.press('Enter'); await pg.wait_for_timeout(80)
        check('Enter returns to the same line', await pg.evaluate(EDITING), '二行目')
        check('and to the same spot', await pg.evaluate(CARET), 2)

        # ↑ / ↓ step to the line above / below
        await pg.keyboard.press('Escape'); await pg.wait_for_timeout(50)
        await pg.keyboard.press('ArrowUp'); await pg.wait_for_timeout(80)
        check('↑ goes one line up', await pg.evaluate(IDX), 0)
        await pg.keyboard.press('Escape'); await pg.wait_for_timeout(50)
        await pg.keyboard.press('ArrowDown'); await pg.wait_for_timeout(80)
        check('↓ goes one line down', await pg.evaluate(IDX), 1)

        # ↑ / ↓ keep the column
        await pg.keyboard.press('Escape'); await pg.wait_for_timeout(50)
        await pg.keyboard.press('ArrowUp'); await pg.wait_for_timeout(80)
        check('↑ keeps the same column', await pg.evaluate(CARET), 2)

        # ← / → step one character from where the caret was (2 in 二行目)
        await pg.click('#blocks .block:nth-child(2)'); await pg.keyboard.press('Home')
        await pg.keyboard.press('ArrowRight'); await pg.keyboard.press('ArrowRight')
        await pg.keyboard.press('Escape'); await pg.wait_for_timeout(50)
        await pg.keyboard.press('ArrowLeft'); await pg.wait_for_timeout(80)
        check('← moves one character left', [await pg.evaluate(IDX), await pg.evaluate(CARET)], [1, 1])
        await pg.keyboard.press('Escape'); await pg.wait_for_timeout(50)
        await pg.keyboard.press('ArrowRight'); await pg.wait_for_timeout(80)
        check('→ moves one character right', [await pg.evaluate(IDX), await pg.evaluate(CARET)], [1, 2])

        # at the edge of a line it steps to the next / previous line
        await pg.keyboard.press('Home'); await pg.keyboard.press('Escape'); await pg.wait_for_timeout(50)
        await pg.keyboard.press('ArrowLeft'); await pg.wait_for_timeout(80)
        check('← at the head goes to the end of the line above', [await pg.evaluate(IDX), await pg.evaluate(CARET)], [0, 3])
        await pg.keyboard.press('End'); await pg.keyboard.press('Escape'); await pg.wait_for_timeout(50)
        await pg.keyboard.press('ArrowRight'); await pg.wait_for_timeout(80)
        check('→ at the end goes to the head of the line below', [await pg.evaluate(IDX), await pg.evaluate(CARET)], [1, 0])
        await pg.keyboard.press('End')

        # typing still works after coming back
        await pg.keyboard.type('！'); await pg.wait_for_timeout(50)
        check('typing lands in the line', await pg.evaluate(EDITING), '二行目！')

        # Tab reaches the text, then Enter starts editing
        await pg.keyboard.press('Escape'); await pg.wait_for_timeout(50)
        await pg.evaluate("document.getElementById('blocks').focus()")
        check('the text can hold focus', await pg.evaluate("document.activeElement.id"), 'blocks')
        await pg.keyboard.press('Enter'); await pg.wait_for_timeout(80)
        check('Enter from there starts editing', await pg.evaluate(EDITING), '二行目！')

        # switching notes forgets the old spot
        await pg.keyboard.press('Escape'); await pg.wait_for_timeout(50)
        await pg.click('#list .item:nth-child(2) .open'); await pg.wait_for_timeout(200)
        await pg.evaluate("document.activeElement.blur()")
        await pg.keyboard.press('Enter'); await pg.wait_for_timeout(80)
        check('another note starts at its first line', await pg.evaluate(IDX), 0)

        # a locked note stays locked
        await pg.keyboard.press('Escape'); await pg.wait_for_timeout(50)
        await pg.click('#lockBtn'); await pg.evaluate("document.activeElement.blur()"); await pg.wait_for_timeout(50)
        await pg.keyboard.press('Enter'); await pg.wait_for_timeout(80)
        check('locked note does not open for editing', await pg.evaluate(EDITING), None)
        check('and says why', 'ロック' in await pg.inner_text('#toast'), True)
        await pg.click('#lockBtn')

        # the find field keeps its own Enter
        await pg.keyboard.press('Control+f'); await pg.wait_for_timeout(100)
        await pg.keyboard.type('二'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(100)
        check('Enter in the find bar does not start editing', await pg.evaluate("document.activeElement.id"), 'fq')
        await b.close()
    print('\nFAILED:', errors if errors else 'none')
asyncio.run(main())
