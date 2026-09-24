import asyncio, os
from playwright.async_api import async_playwright
# moving up/down between lines keeps the column the caret looks like it is in
errors = []
def check(label, got, want=True):
    ok = got == want
    print(('OK  ' if ok else 'NG  ') + label + ('' if ok else '  -> got ' + repr(got) + ' want ' + repr(want)))
    if not ok: errors.append(label)
WHERE = """(() => { const el = document.querySelector('#blocks .editing'); if (!el) return ['-', -1];
  const s = getSelection(); if (!s.rangeCount) return [el._raw, -1]; const r = s.getRangeAt(0);
  const pre = document.createRange(); pre.selectNodeContents(el); pre.setEnd(r.startContainer, r.startOffset);
  return [el._raw, pre.toString().length]; })()"""
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page()
        pg.on("pageerror", lambda e: errors.append('pageerror: ' + str(e)) or print("PAGEERROR", e))
        await pg.goto("file://" + os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "index.html"))); await pg.wait_for_timeout(300)
        await pg.click('[data-choice=browser]')
        await pg.click('#newNote'); await pg.wait_for_timeout(50)
        for i, t in enumerate(['あいうえおかきくけこ', 'さしすせそ', 'たちつてとなにぬねの']):
            if i: await pg.keyboard.press('Enter')
            await pg.keyboard.type(t)
        await pg.wait_for_timeout(80)
        async def at(line, col):
            await pg.click('#blocks .block:nth-child(%d)' % line); await pg.keyboard.press('Home')
            for _ in range(col): await pg.keyboard.press('ArrowRight')
            await pg.wait_for_timeout(50)

        # --- while editing
        await at(2, 2)
        await pg.keyboard.press('ArrowUp'); await pg.wait_for_timeout(80)
        check('↑ keeps the column', await pg.evaluate(WHERE), ['あいうえおかきくけこ', 2])
        await pg.keyboard.press('ArrowDown'); await pg.wait_for_timeout(80)
        check('↓ keeps it too', await pg.evaluate(WHERE), ['さしすせそ', 2])
        await pg.keyboard.press('ArrowDown'); await pg.wait_for_timeout(80)
        check('and again on the next line', await pg.evaluate(WHERE), ['たちつてとなにぬねの', 2])

        # --- a short line takes the caret as far as it goes
        await at(1, 8)
        await pg.keyboard.press('ArrowDown'); await pg.wait_for_timeout(80)
        check('a shorter line stops at its end', await pg.evaluate(WHERE), ['さしすせそ', 5])

        # --- the column survives Esc: the same move from the waiting state
        await at(2, 2)
        await pg.keyboard.press('Escape'); await pg.wait_for_timeout(60)
        await pg.keyboard.press('ArrowUp'); await pg.wait_for_timeout(80)
        check('↑ after Esc keeps the column', await pg.evaluate(WHERE), ['あいうえおかきくけこ', 2])
        await pg.keyboard.press('Escape'); await pg.wait_for_timeout(60)
        await pg.keyboard.press('ArrowDown'); await pg.wait_for_timeout(80)
        check('↓ after Esc keeps it', await pg.evaluate(WHERE), ['さしすせそ', 2])

        # --- Enter still returns to the exact spot, ←→ still step one character
        await at(2, 3)
        await pg.keyboard.press('Escape'); await pg.wait_for_timeout(60)
        await pg.keyboard.press('Enter'); await pg.wait_for_timeout(80)
        check('Enter returns to the same spot', await pg.evaluate(WHERE), ['さしすせそ', 3])
        await pg.keyboard.press('Escape'); await pg.wait_for_timeout(60)
        await pg.keyboard.press('ArrowLeft'); await pg.wait_for_timeout(80)
        check('← still steps one character', await pg.evaluate(WHERE), ['さしすせそ', 2])
        await b.close()
    print('\nFAILED:', errors if errors else 'none')
asyncio.run(main())
