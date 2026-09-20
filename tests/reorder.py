import asyncio
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page()
        pg.on("pageerror", lambda e: print("pageerror:", e))
        await pg.goto("file://" + __import__("os").path.abspath(__import__("os").path.join(__import__("os").path.dirname(__file__), "..", "index.html")) + ""); await pg.wait_for_timeout(300)
        await pg.click('[data-choice=browser]')
        for t in ['A','B','C']:
            await pg.click('#newNote'); await pg.keyboard.type('# '+t); await pg.wait_for_timeout(50)
        titles = "[...document.querySelectorAll('#list .item .t')].map(e=>e.textContent)"
        print("initial:", await pg.evaluate(titles))
        # edit B: order should not change
        await pg.click('#list .item:nth-child(2) .open'); await pg.click('#blocks .block'); await pg.keyboard.press('End'); await pg.keyboard.type('!'); await pg.wait_for_timeout(50)
        print("after edit B:", await pg.evaluate(titles))
        # drag C (1st) below A (3rd)
        src = pg.locator('#list .item:nth-child(1) .open'); dst = pg.locator('#list .item:nth-child(3) .open')
        sb = await src.bounding_box(); db = await dst.bounding_box()
        await pg.mouse.move(sb['x']+40, sb['y']+10); await pg.mouse.down()
        await pg.mouse.move(sb['x']+40, sb['y']+20, steps=3); await pg.mouse.move(db['x']+40, db['y']+db['height']-4, steps=10); await pg.wait_for_timeout(50)
        await pg.mouse.up(); await pg.wait_for_timeout(100)
        print("after drag:", await pg.evaluate(titles))
        await pg.reload(); await pg.wait_for_timeout(300)
        print("after reload:", await pg.evaluate(titles))
        await b.close()
asyncio.run(main())
