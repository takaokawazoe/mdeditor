import asyncio, os
from playwright.async_api import async_playwright
# Ctrl+B / I / E wrap the text, and take the markers off again when pressed a second time
errors = []
def check(label, got, want):
    ok = got == want
    print(('OK  ' if ok else 'NG  ') + label + ('' if ok else '  -> got ' + repr(got) + ' want ' + repr(want)))
    if not ok: errors.append(label)
RAW = "document.querySelector('#blocks .editing')._raw"
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page()
        pg.on("pageerror", lambda e: errors.append('pageerror: ' + str(e)) or print("PAGEERROR", e))
        await pg.goto("file://" + os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "index.html"))); await pg.wait_for_timeout(300)
        await pg.click('[data-choice=browser]')
        async def fresh(text):
            await pg.click('#newNote'); await pg.wait_for_timeout(50)
            await pg.keyboard.type(text); await pg.wait_for_timeout(50)
        async def caret(off):  # move the caret with real keys: Home, then → off times
            await pg.keyboard.press('Home')
            for _ in range(off): await pg.keyboard.press('ArrowRight')
        async def select(a, b_):
            await caret(a)
            for _ in range(b_ - a): await pg.keyboard.press('Shift+ArrowRight')
        async def raw(): return await pg.evaluate(RAW)

        # --- bold on a selection, then off
        await fresh('あいうえお')
        await select(1, 3); await pg.keyboard.press('Control+b')
        check('bold wraps the selection', await raw(), 'あ**いう**えお')
        check('the text stays selected', await pg.evaluate("getSelection().toString()"), 'いう')
        await pg.keyboard.press('Control+b')
        check('pressing again takes it off', await raw(), 'あいうえお')
        check('the text is still selected', await pg.evaluate("getSelection().toString()"), 'いう')

        # --- the caret sitting in the bold text
        await fresh('**太字**のテスト')
        await caret(4); await pg.keyboard.press('Control+b')
        check('caret inside: markers come off', await raw(), '太字のテスト')

        # --- the caret right after the closing markers (what happens after wrapping)
        await fresh('**太字**')
        await caret(8); await pg.keyboard.press('Control+b')
        check('caret just after: markers come off', await raw(), '太字')

        # --- an empty pair is cancelled instead of piling up asterisks
        await fresh('文字')
        await pg.keyboard.press('Control+b')
        check('empty pair inserted', await raw(), '文字****')
        await pg.keyboard.press('Control+b')
        check('second press cancels it', await raw(), '文字')
        await pg.keyboard.press('Control+b'); await pg.keyboard.press('Control+b'); await pg.keyboard.press('Control+b')
        check('three more presses leave one pair', await raw(), '文字****')

        # --- italic and code behave the same way
        await fresh('斜体テスト')
        await select(0, 2); await pg.keyboard.press('Control+i')
        check('italic wraps', await raw(), '*斜体*テスト')
        await pg.keyboard.press('Control+i')
        check('italic comes off', await raw(), '斜体テスト')
        await select(0, 2); await pg.keyboard.press('Control+e')
        check('code wraps', await raw(), '`斜体`テスト')
        await pg.keyboard.press('Control+e')
        check('code comes off', await raw(), '斜体テスト')

        # --- nested: italic inside bold, each toggle minds its own markers
        await fresh('あ')
        await select(0, 1); await pg.keyboard.press('Control+b'); await pg.keyboard.press('Control+i')
        check('bold + italic', await raw(), '***あ***')
        await pg.keyboard.press('Control+i')
        check('italic off, bold kept', await raw(), '**あ**')
        await pg.keyboard.press('Control+b')
        check('bold off too', await raw(), 'あ')

        # --- italic inside an existing bold span
        await fresh('**太字と斜体**')
        await select(4, 6); await pg.keyboard.press('Control+i')
        check('italic inside bold', await raw(), '**太字*と斜*体**')
        await pg.keyboard.press('Control+i')
        check('italic off again', await raw(), '**太字と斜体**')

        # --- two bold spans on one line: the caret picks its own
        await fresh('**A**と**B**')
        await caret(9); await pg.keyboard.press('Control+b')
        check('only the second span changes', await raw(), '**A**とB')

        # --- undo brings the markers back
        await pg.keyboard.press('Control+z'); await pg.wait_for_timeout(150)
        line = await pg.evaluate("[...document.querySelectorAll('#blocks .block')].map(e=>e._raw).join('\\n')")
        check('undo restores', line, '**A**と**B**')
        await b.close()
    print('\nFAILED:', errors if errors else 'none')
asyncio.run(main())
