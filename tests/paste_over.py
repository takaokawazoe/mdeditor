import asyncio, os
from playwright.async_api import async_playwright
# pasting while whole lines are selected replaces them; with nothing selected, paste does nothing
errors = []
def check(label, got, want=True):
    ok = got == want
    print(('OK  ' if ok else 'NG  ') + label + ('' if ok else '  -> got ' + repr(got) + ' want ' + repr(want)))
    if not ok: errors.append(label)
RAWS = "[...document.querySelectorAll('#blocks .block')].map(e=>e._raw)"
SEL = "[...document.querySelectorAll('#blocks .block')].map((e,i)=>e.classList.contains('bsel')?i:-1).filter(i=>i>=0)"
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(permissions=['clipboard-read', 'clipboard-write']); pg = await ctx.new_page()
        pg.on("pageerror", lambda e: errors.append('pageerror: ' + str(e)) or print("PAGEERROR", e))
        await pg.goto("file://" + os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "index.html"))); await pg.wait_for_timeout(300)
        await pg.click('[data-choice=browser]')
        async def setclip(t): await pg.evaluate("t=>navigator.clipboard.writeText(t)", t)
        async def note(lines):
            await pg.click('#newNote'); await pg.wait_for_timeout(50)
            for i, l in enumerate(lines):
                if i: await pg.keyboard.press('Enter')
                await pg.keyboard.type(l)
            await pg.wait_for_timeout(50)

        # --- replace two selected lines with two pasted ones
        await note(['一', '二', '三'])
        await setclip('貼りA\n貼りB')
        await pg.click('#blocks .block:nth-child(1)'); await pg.keyboard.press('Shift+ArrowDown'); await pg.wait_for_timeout(50)
        check('two lines selected', await pg.evaluate(SEL), [0, 1])
        await pg.keyboard.press('Control+v'); await pg.wait_for_timeout(150)
        check('the selected lines are replaced', await pg.evaluate(RAWS), ['貼りA', '貼りB', '三'])
        check('editing continues on the last pasted line', await pg.evaluate("document.querySelector('#blocks .editing')?._raw"), '貼りB')
        check('the selection is gone', await pg.evaluate(SEL), [])

        # --- undo puts the old lines back in one step
        await pg.keyboard.press('Control+z'); await pg.wait_for_timeout(150)
        check('undo restores the lines', await pg.evaluate(RAWS), ['一', '二', '三'])

        # --- a single pasted line over the whole note
        await setclip('まとめて一行')
        await pg.click('#blocks .block:nth-child(1)'); await pg.keyboard.press('Control+a'); await pg.wait_for_timeout(50)
        await pg.keyboard.press('Control+v'); await pg.wait_for_timeout(150)
        check('everything becomes one line', await pg.evaluate(RAWS), ['まとめて一行'])

        # --- nothing selected: paste does nothing
        await pg.keyboard.press('Escape'); await pg.evaluate("document.activeElement.blur()"); await pg.wait_for_timeout(80)
        await setclip('入ってはいけない')
        await pg.keyboard.press('Control+v'); await pg.wait_for_timeout(150)
        check('idle paste changes nothing', await pg.evaluate(RAWS), ['まとめて一行'])
        check('and starts no editing', await pg.evaluate("!!document.querySelector('#blocks .editing')"), False)

        # --- pasting while editing still works as before
        await pg.click('#blocks .block:nth-child(1)'); await pg.keyboard.press('End')
        await setclip('・追記')
        await pg.keyboard.press('Control+v'); await pg.wait_for_timeout(150)
        check('paste inside a line still inserts', await pg.evaluate(RAWS), ['まとめて一行・追記'])

        # --- a locked note refuses
        await pg.keyboard.press('Escape'); await pg.wait_for_timeout(50)
        await pg.click('#lockBtn'); await pg.evaluate("document.activeElement.blur()"); await pg.wait_for_timeout(50)
        await pg.keyboard.press('Control+a'); await pg.wait_for_timeout(50)
        await setclip('ロック中')
        await pg.keyboard.press('Control+v'); await pg.wait_for_timeout(150)
        check('locked note is untouched', await pg.evaluate(RAWS), ['まとめて一行・追記'])
        check('and says why', 'ロック' in await pg.inner_text('#toast'))
        await b.close()
    print('\nFAILED:', errors if errors else 'none')
asyncio.run(main())
