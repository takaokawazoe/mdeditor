import asyncio
from playwright.async_api import async_playwright
# theme (OS / light / dark), palettes, and per-colour overrides
# needs `python3 -m http.server 8123` (a reload has to keep the settings)
URL = "http://localhost:8123/index.html"
errors = []
def check(label, got, want=True):
    ok = got == want
    print(('OK  ' if ok else 'NG  ') + label + ('' if ok else '  -> got ' + repr(got) + ' want ' + repr(want)))
    if not ok: errors.append(label)
VAR = "v=>getComputedStyle(document.documentElement).getPropertyValue('--'+v).trim()"
BG = "getComputedStyle(document.body).backgroundColor"
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        light = await b.new_context(color_scheme='light'); pg = await light.new_page()
        pg.on("pageerror", lambda e: errors.append('pageerror: ' + str(e)) or print("PAGEERROR", e))
        await pg.goto(URL); await pg.wait_for_timeout(400); await pg.click('[data-choice=browser]')
        await pg.click('#settingsBtn'); await pg.wait_for_timeout(150)
        check('starts on the default palette', await pg.evaluate(VAR, 'accent'), '#2F5BC7')
        check('every colour has a swatch', await pg.evaluate("document.querySelectorAll('#colorList .swatch').length"), 9)

        # --- palettes
        await pg.select_option('#sPalette', 'sepia'); await pg.wait_for_timeout(150)
        check('sepia paper', await pg.evaluate(VAR, 'paper'), '#FBF5E9')
        check('the editor really uses it', await pg.evaluate("getComputedStyle(document.querySelector('.main')).backgroundColor"), 'rgb(251, 245, 233)')

        # --- one colour changed by hand
        await pg.evaluate("""(() => { const i = document.querySelector('#colorList .swatch[data-v=accent] input');
            i.value = '#ff0000'; i.dispatchEvent(new Event('input', {bubbles:true})); })()"""); await pg.wait_for_timeout(150)
        check('the accent follows the picker', await pg.evaluate(VAR, 'accent'), '#ff0000')
        check('its 既定 button turns on', await pg.evaluate("!document.querySelector('#colorList .swatch[data-v=accent] [data-cdef]').disabled"))

        # --- it survives a reload
        await pg.reload(); await pg.wait_for_timeout(500)
        check('kept after a reload', [await pg.evaluate(VAR, 'accent'), await pg.evaluate(VAR, 'paper')], ['#ff0000', '#FBF5E9'])

        # --- back to the palette colour
        await pg.click('#settingsBtn'); await pg.wait_for_timeout(200)
        await pg.click('#colorList .swatch[data-v=accent] [data-cdef]'); await pg.wait_for_timeout(150)
        check('既定 puts the palette colour back', await pg.evaluate(VAR, 'accent'), '#9A5B2E')

        # --- switching the palette clears colours changed by hand
        await pg.evaluate("""(() => { const i = document.querySelector('#colorList .swatch[data-v=ink] input');
            i.value = '#123456'; i.dispatchEvent(new Event('input', {bubbles:true})); })()"""); await pg.wait_for_timeout(100)
        await pg.select_option('#sPalette', 'gray'); await pg.wait_for_timeout(200)
        check('changed colours are dropped', await pg.evaluate(VAR, 'ink'), '#1F1F1F')
        check('and it says so', '個別に変えた色は戻しました' in await pg.inner_text('#toast'))

        # --- dark by hand, on a machine set to light
        await pg.select_option('#sTheme', 'dark'); await pg.wait_for_timeout(200)
        check('dark is applied', await pg.evaluate(VAR, 'paper'), '#1E1E1E')
        check('data-theme is set', await pg.evaluate("document.documentElement.dataset.theme"), 'dark')
        check('the swatches show the dark colours', await pg.evaluate("document.querySelector('#colorList .swatch[data-v=paper] input').value"), '#1e1e1e')
        await pg.evaluate("""(() => { const i = document.querySelector('#colorList .swatch[data-v=paper] input');
            i.value = '#101010'; i.dispatchEvent(new Event('input', {bubbles:true})); })()"""); await pg.wait_for_timeout(150)
        check('a dark colour can be changed', await pg.evaluate(VAR, 'paper'), '#101010')
        await pg.select_option('#sTheme', 'light'); await pg.wait_for_timeout(200)
        check('the light colours are untouched', await pg.evaluate(VAR, 'paper'), '#FFFFFF')
        await pg.select_option('#sTheme', 'dark'); await pg.wait_for_timeout(150)
        check('and the dark one is still there', await pg.evaluate(VAR, 'paper'), '#101010')

        # --- everything back to default
        await pg.click('#colorsReset'); await pg.wait_for_timeout(200)
        check('reset clears palette, theme and colours', [await pg.evaluate(VAR, 'accent'), await pg.evaluate(VAR, 'paper'), await pg.evaluate("document.documentElement.dataset.theme ?? ''")], ['#2F5BC7', '#FFFFFF', ''])
        await light.close()

        # --- a machine set to dark starts dark
        dark = await b.new_context(color_scheme='dark'); dp = await dark.new_page()
        await dp.goto(URL); await dp.wait_for_timeout(400); await dp.click('[data-choice=browser]')
        check('follows the OS', await dp.evaluate(VAR, 'paper'), '#1B1F28')
        await dp.click('#settingsBtn'); await dp.wait_for_timeout(150)
        check('the hint names the mode being edited', '暗い外観の色を編集しています' in await dp.inner_text('#colorHint'))
        await dp.select_option('#sTheme', 'light'); await dp.wait_for_timeout(200)
        check('light can be forced on a dark machine', await dp.evaluate(VAR, 'paper'), '#FFFFFF')
        await b.close()
    print('\nFAILED:', errors if errors else 'none')
asyncio.run(main())
