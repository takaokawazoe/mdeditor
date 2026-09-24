import asyncio, os
from playwright.async_api import async_playwright
# a selection that leaves its line merges those lines into one editable element,
# so character-level selection, copying and typing work across lines
errors = []
def check(label, got, want=True):
    ok = got == want
    print(('OK  ' if ok else 'NG  ') + label + ('' if ok else '  -> got ' + repr(got) + ' want ' + repr(want)))
    if not ok: errors.append(label)
RAWS = "[...document.querySelectorAll('#blocks .block')].map(e=>e._raw)"
MERGED = "document.querySelector('#blocks .merged')?._raw ?? null"
SEL = "getSelection().toString()"
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(permissions=['clipboard-read', 'clipboard-write']); pg = await ctx.new_page()
        pg.on("pageerror", lambda e: errors.append('pageerror: ' + str(e)) or print("PAGEERROR", e))
        await pg.goto("file://" + os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "index.html"))); await pg.wait_for_timeout(300)
        await pg.click('[data-choice=browser]')
        async def note(lines):
            await pg.click('#newNote'); await pg.wait_for_timeout(50)
            for i, l in enumerate(lines):
                if i: await pg.keyboard.press('Enter')
                await pg.keyboard.type(l)
            await pg.wait_for_timeout(80)

        # --- Shift+↓ from a line reaches into the next one
        await note(['あいうえお', 'かきくけこ', 'さしすせそ'])
        await pg.click('#blocks .block:nth-child(1)'); await pg.keyboard.press('Home')
        for _ in range(2): await pg.keyboard.press('ArrowRight')
        await pg.keyboard.press('Shift+ArrowDown'); await pg.wait_for_timeout(100)
        check('the lines are merged into one element', await pg.evaluate(MERGED), 'あいうえお\nかきくけこ')
        check('the selection crosses the line break', await pg.evaluate(SEL), 'うえお\nかき')
        await pg.keyboard.press('Shift+ArrowRight'); await pg.wait_for_timeout(60)
        check('and keeps growing by character', await pg.evaluate(SEL), 'うえお\nかきく')

        # --- copying takes exactly what is selected
        await pg.keyboard.press('Control+c'); await pg.wait_for_timeout(150)
        check('the clipboard holds the exact range', await pg.evaluate("navigator.clipboard.readText()"), 'うえお\nかきく')

        # --- typing replaces the selection across the lines
        await pg.keyboard.type('X'); await pg.wait_for_timeout(120)
        check('typing replaces it', await pg.evaluate(MERGED), 'あいXけこ')
        await pg.keyboard.press('Control+z'); await pg.wait_for_timeout(200)
        check('undo brings the two lines back', await pg.evaluate(RAWS), ['あいうえお', 'かきくけこ', 'さしすせそ'])

        # --- Esc splits the lines apart again
        await pg.click('#blocks .block:nth-child(1)'); await pg.keyboard.press('Home')
        await pg.keyboard.press('Shift+ArrowDown'); await pg.wait_for_timeout(100)
        check('merged again', await pg.evaluate(MERGED) is not None)
        await pg.keyboard.press('Escape'); await pg.wait_for_timeout(120)
        check('back to one line per block', await pg.evaluate(RAWS), ['あいうえお', 'かきくけこ', 'さしすせそ'])
        check('nothing is merged', await pg.evaluate(MERGED), None)

        # --- dragging across lines selects by character
        await note(['ドラッグ元の行', '途中の行', 'ここまでの行'])
        await pg.click('#blocks .block:nth-child(1)'); await pg.keyboard.press('Escape'); await pg.wait_for_timeout(80)
        b1 = await pg.locator('#blocks .block:nth-child(1)').bounding_box()
        b3 = await pg.locator('#blocks .block:nth-child(3)').bounding_box()
        await pg.mouse.move(b1['x'] + 60, b1['y'] + b1['height'] / 2); await pg.mouse.down()
        await pg.mouse.move(b1['x'] + 90, b1['y'] + b1['height'] / 2, steps=3)
        await pg.mouse.move(b3['x'] + 60, b3['y'] + b3['height'] / 2, steps=8); await pg.wait_for_timeout(120)
        await pg.mouse.up(); await pg.wait_for_timeout(80)
        sel = await pg.evaluate(SEL)
        check('the drag crosses both breaks', sel.count('\n'), 2)
        check('it starts inside the first line', sel[0] != 'ド' and 'ドラッグ' not in sel, True)

        # --- line commands still work on the lines the selection touches
        await note(['- あ', 'い', 'う'])
        await pg.click('#blocks .block:nth-child(1)'); await pg.keyboard.press('Home')
        await pg.keyboard.press('Shift+ArrowDown'); await pg.wait_for_timeout(100)
        await pg.keyboard.press('Tab'); await pg.wait_for_timeout(100)
        check('Tab indents every touched line', await pg.evaluate(MERGED), '  - あ\n  - い')
        await pg.keyboard.press('Shift+Tab'); await pg.wait_for_timeout(100)
        check('Shift+Tab puts them back', await pg.evaluate(MERGED), '- あ\n- い')
        await pg.keyboard.press('Alt+Shift+ArrowDown'); await pg.wait_for_timeout(120)
        check('Alt+Shift+↓ moves them down', await pg.evaluate(MERGED), '- う\n- あ\n- い')

        # --- a table inside the range survives the round trip
        await note(['見出しの行'])
        await pg.keyboard.press('Enter'); await pg.keyboard.type('| a | b |'); await pg.keyboard.press('Enter')
        await pg.keyboard.type('1 | 2 |'); await pg.keyboard.press('Escape'); await pg.wait_for_timeout(150)
        before = await pg.evaluate(RAWS)
        check('the table is one block of several lines', len(before), 2)
        await pg.click('#blocks .block:nth-child(1)'); await pg.keyboard.press('Home')
        for _ in range(3): await pg.keyboard.press('Shift+ArrowDown')
        await pg.wait_for_timeout(120)
        check('the table got merged in', '---' in (await pg.evaluate(MERGED) or ''), True)
        await pg.keyboard.press('Escape'); await pg.wait_for_timeout(150)
        check('the blocks come back as they were', await pg.evaluate(RAWS), before)

        # --- a locked note does not merge
        await pg.click('#lockBtn'); await pg.wait_for_timeout(50)
        await pg.evaluate("document.activeElement.blur()")
        await pg.click('#blocks .block:nth-child(1)'); await pg.wait_for_timeout(80)
        check('locked: no editing, no merging', [await pg.evaluate(MERGED), await pg.evaluate("!!document.querySelector('#blocks .editing')")], [None, False])
        await pg.click('#lockBtn')
        await b.close()
    print('\nFAILED:', errors if errors else 'none')
asyncio.run(main())
