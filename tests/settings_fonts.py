import asyncio
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page()
        pg.on("pageerror", lambda e: print("pageerror:", e))
        await pg.goto("file://" + __import__("os").path.abspath(__import__("os").path.join(__import__("os").path.dirname(__file__), "..", "index.html")) + ""); await pg.wait_for_timeout(300)
        await pg.click('[data-choice=browser]')
        await pg.click('#settingsBtn'); await pg.wait_for_timeout(50)
        await pg.select_option('#sBody', 'notoserif'); await pg.fill('#sSize', '18'); await pg.evaluate("document.getElementById('sSize').dispatchEvent(new Event('input'))")
        await pg.wait_for_timeout(50)
        print(await pg.evaluate("[getComputedStyle(document.querySelector('#blocks .block')).fontFamily.slice(0,40), getComputedStyle(document.getElementById('editor')).fontSize, [...document.querySelectorAll('link[href*=googleapis]')].map(l=>l.href.slice(40,70))]"))
        await pg.select_option('#sMono', 'custom'); await pg.fill('#sMonoCustom', 'Consolas'); await pg.wait_for_timeout(50)
        print(await pg.evaluate("getComputedStyle(document.querySelector('.b-code')).fontFamily.slice(0,30)"))
        await pg.reload(); await pg.wait_for_timeout(300)
        print("persisted:", await pg.evaluate("[getComputedStyle(document.getElementById('editor')).fontSize, getComputedStyle(document.querySelector('#blocks .block')).fontFamily.slice(0,20)]"))
        await b.close()
asyncio.run(main())
