import asyncio
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page()
        pg.on("pageerror", lambda e: print("pageerror:", e))
        await pg.goto("file://" + __import__("os").path.abspath(__import__("os").path.join(__import__("os").path.dirname(__file__), "..", "index.html")) + ""); await pg.wait_for_timeout(300)
        await pg.click('[data-choice=browser]')
        print("list:", await pg.evaluate("[...document.querySelectorAll('#list .item .t')].map(e=>e.textContent)"))
        await pg.click('#helpBtn'); await pg.wait_for_timeout(100)
        print("manual open:", await pg.evaluate("document.getElementById('title').textContent"), "lock btn:", await pg.evaluate("document.getElementById('lockBtn').textContent"), "tables:", await pg.evaluate("document.querySelectorAll('#blocks table').length"))
        await pg.click('#blocks .block:nth-child(3)'); await pg.wait_for_timeout(50)
        print("editing while locked:", await pg.evaluate("!!document.querySelector('.editing')"), "toast:", await pg.evaluate("document.getElementById('toast').textContent"))
        print("x hidden:", await pg.evaluate("!document.querySelector('#list .item.active .x')"))
        await pg.click('#lockBtn'); await pg.wait_for_timeout(50)
        await pg.click('#blocks .block:nth-child(3)'); await pg.wait_for_timeout(50)
        print("editing after unlock:", await pg.evaluate("!!document.querySelector('.editing')"))
        await pg.click('#lockBtn'); await pg.wait_for_timeout(50)
        print("re-locked, editing cleared:", await pg.evaluate("!document.querySelector('.editing')"))
        # unlock, delete, then ? re-creates
        await pg.click('#lockBtn'); await pg.hover('#list .item.active'); await pg.click('#list .item.active .x'); await pg.click('#list [data-act=del]'); await pg.wait_for_timeout(100)
        print("after delete:", await pg.evaluate("[...document.querySelectorAll('#list .item .t')].map(e=>e.textContent)"))
        await pg.click('#helpBtn'); await pg.wait_for_timeout(100)
        print("recreated:", await pg.evaluate("[...document.querySelectorAll('#list .item .t')].map(e=>e.textContent)"), await pg.evaluate("document.getElementById('lockBtn').textContent"))
        await b.close()
asyncio.run(main())
