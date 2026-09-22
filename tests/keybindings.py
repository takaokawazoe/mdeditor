import asyncio
from playwright.async_api import async_playwright
# rebinding shortcuts from the settings dialog, and the three commands that ship with no key
# needs `python3 -m http.server 8123` (a reload has to keep the settings)
URL = "http://localhost:8123/index.html"
errors = []
def check(label, got, want=True):
    ok = got == want
    print(('OK  ' if ok else 'NG  ') + label + ('' if ok else '  -> got ' + repr(got) + ' want ' + repr(want)))
    if not ok: errors.append(label)
EDITING = "document.querySelector('#blocks .editing')?._raw ?? null"
RAWS = "[...document.querySelectorAll('#blocks .block')].map(e=>e._raw)"
CARET = """(() => { const el = document.querySelector('#blocks .editing'); if (!el) return -1;
  const s = getSelection(); if (!s.rangeCount) return -1; const r = s.getRangeAt(0);
  const pre = document.createRange(); pre.selectNodeContents(el); pre.setEnd(r.startContainer, r.startOffset); return pre.toString().length; })()"""
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); ctx = await b.new_context(viewport={'width': 1100, 'height': 900}); pg = await ctx.new_page()
        pg.on("pageerror", lambda e: errors.append('pageerror: ' + str(e)) or print("PAGEERROR", e))
        await pg.goto(URL); await pg.wait_for_timeout(400); await pg.click('[data-choice=browser]')
        async def bind(cmd, *keys):  # press 「変更」 then the keystroke(s)
            await pg.evaluate("id=>document.querySelector('#keysList .krow[data-id='+id+'] [data-k=set]').click()", cmd)
            for k in keys: await pg.keyboard.press(k)
            await pg.wait_for_timeout(50)
        async def shown(cmd):
            return await pg.evaluate("id=>document.querySelector('#keysList .krow[data-id='+id+'] .kk').textContent", cmd)
        async def line(text):
            await pg.click('#newNote'); await pg.wait_for_timeout(50)
            await pg.keyboard.type(text); await pg.wait_for_timeout(50)

        await pg.click('#settingsBtn'); await pg.wait_for_timeout(150)
        check('every command is listed', await pg.evaluate("document.querySelectorAll('#keysList .krow').length"), 14)
        check('unbound commands show a dash', await shown('strike'), '—')

        # --- bind the three that ship with no key
        await bind('strike', 'Control+Shift+X'); check('strike shows its new key', await shown('strike'), 'Ctrl+Shift+X')
        await bind('quote', 'Control+Shift+Q'); await bind('link', 'Control+Shift+K')
        await pg.click('#sClose'); await pg.wait_for_timeout(100)

        await line('あいうえお')
        await pg.keyboard.press('Home')
        for _ in range(2): await pg.keyboard.press('Shift+ArrowRight')
        await pg.keyboard.press('Control+Shift+X'); await pg.wait_for_timeout(50)
        check('strike wraps', await pg.evaluate(EDITING), '~~あい~~うえお')
        await pg.keyboard.press('Control+Shift+X'); await pg.wait_for_timeout(50)
        check('strike toggles off', await pg.evaluate(EDITING), 'あいうえお')

        # --- quote, on one line and on a selection of lines
        await pg.keyboard.press('End'); await pg.keyboard.press('Control+Shift+Q'); await pg.wait_for_timeout(50)
        check('quote added', await pg.evaluate(EDITING), '> あいうえお')
        check('caret moved with the text', await pg.evaluate(CARET), 7)
        await pg.keyboard.press('Home')
        for _ in range(4): await pg.keyboard.press('Shift+ArrowRight')
        await pg.keyboard.press('Control+Shift+Q'); await pg.wait_for_timeout(50)
        check('a selection is kept', await pg.evaluate("getSelection().toString()"), 'あい')
        await pg.keyboard.press('Control+Shift+Q'); await pg.wait_for_timeout(50)
        check('quote back on', await pg.evaluate(EDITING), '> あいうえお')
        await pg.keyboard.press('End')
        await pg.keyboard.press('Control+Shift+Q'); await pg.wait_for_timeout(50)
        check('quote removed', await pg.evaluate(EDITING), 'あいうえお')
        await pg.keyboard.press('Enter'); await pg.keyboard.type('二行目'); await pg.wait_for_timeout(50)
        await pg.keyboard.press('Shift+ArrowUp'); await pg.wait_for_timeout(50)
        await pg.keyboard.press('Control+Shift+Q'); await pg.wait_for_timeout(80)
        check('quote on selected lines', await pg.evaluate(RAWS), ['> あいうえお', '> 二行目'])
        await pg.keyboard.press('Control+Shift+Q'); await pg.wait_for_timeout(80)
        check('quote off again', await pg.evaluate(RAWS), ['あいうえお', '二行目'])

        # --- link, with and without a selection
        await pg.click('#blocks .block:nth-child(2)'); await pg.keyboard.press('Home')
        for _ in range(3): await pg.keyboard.press('Shift+ArrowRight')
        await pg.keyboard.press('Control+Shift+K'); await pg.wait_for_timeout(50)
        check('selection becomes the link text', await pg.evaluate(EDITING), '[二行目]()')
        check('caret waits inside the parens', await pg.evaluate(CARET), 6)
        await pg.keyboard.type('https://例'); await pg.wait_for_timeout(50)
        check('the URL lands there', await pg.evaluate(EDITING), '[二行目](https://例)')
        await pg.keyboard.press('End'); await pg.keyboard.press('Control+Shift+K'); await pg.wait_for_timeout(50)
        check('with no selection an empty link is inserted', await pg.evaluate(EDITING), '[二行目](https://例)[]()')
        check('caret waits inside the brackets', await pg.evaluate(CARET), 17)
        await pg.keyboard.press('Control+Shift+K'); await pg.wait_for_timeout(50)
        check('pressing again takes the empty link back', await pg.evaluate(EDITING), '[二行目](https://例)')

        # --- moving a key away from another command
        await pg.click('#settingsBtn'); await pg.wait_for_timeout(150)
        await bind('strike', 'Control+B')
        check('a clash is not taken at once', await shown('strike'), 'キーを押してください')
        check('and it says so', 'に割り当たっています' in await pg.inner_text('#toast'))
        await pg.keyboard.press('Control+B'); await pg.wait_for_timeout(80)
        check('pressing again moves it', await shown('strike'), 'Ctrl+B')
        check('the old owner loses it', await shown('bold'), '—')
        await pg.click('#sClose'); await pg.wait_for_timeout(100)
        await pg.click('#blocks .block:nth-child(1)'); await pg.keyboard.press('Home')
        for _ in range(2): await pg.keyboard.press('Shift+ArrowRight')
        await pg.keyboard.press('Control+b'); await pg.wait_for_timeout(50)
        check('Ctrl+B now strikes through', await pg.evaluate(EDITING), '~~あい~~うえお')

        # --- structural keys are refused
        await pg.click('#settingsBtn'); await pg.wait_for_timeout(150)
        await bind('italic', 'Enter')
        check('Enter is refused', await shown('italic'), 'キーを押してください')
        check('and says why', 'キーは本文の操作に使う' in await pg.inner_text('#toast'))
        await pg.keyboard.press('Escape'); await pg.wait_for_timeout(50)
        check('Esc stops waiting', await shown('italic'), 'Ctrl+I')

        # --- clearing and restoring
        await pg.evaluate("document.querySelector('#keysList .krow[data-id=save] [data-k=clear]').click()"); await pg.wait_for_timeout(50)
        check('cleared to none', await shown('save'), '—')
        # --- kept after a reload
        await pg.reload(); await pg.wait_for_timeout(500)
        await pg.click('#settingsBtn'); await pg.wait_for_timeout(200)
        check('settings survive a reload', [await shown('strike'), await shown('bold'), await shown('save')], ['Ctrl+B', '—', '—'])
        await pg.click('#keysReset'); await pg.wait_for_timeout(100)
        check('all back to default', [await shown('strike'), await shown('bold'), await shown('save')], ['—', 'Ctrl+B', 'Ctrl+S'])
        await pg.click('#sClose'); await pg.wait_for_timeout(100)
        await line('ぼーるど')
        await pg.keyboard.press('Home')
        for _ in range(4): await pg.keyboard.press('Shift+ArrowRight')
        await pg.keyboard.press('Control+b'); await pg.wait_for_timeout(50)
        check('Ctrl+B is bold again', await pg.evaluate(EDITING), '**ぼーるど**')

        # --- the section is not shown on a phone
        m = await (await b.new_context(viewport={'width': 390, 'height': 700}, has_touch=True, is_mobile=True)).new_page()
        await m.goto(URL); await m.wait_for_timeout(400); await m.tap('[data-choice=browser]')
        await m.tap('#menu'); await m.wait_for_timeout(200); await m.tap('#settingsBtn'); await m.wait_for_timeout(200)
        check('hidden on a phone', await m.evaluate("document.getElementById('keysSection').hidden"))
        await b.close()
    print('\nFAILED:', errors if errors else 'none')
asyncio.run(main())
