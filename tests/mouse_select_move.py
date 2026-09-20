import asyncio
from playwright.async_api import async_playwright
R = "[...document.querySelectorAll('#blocks .block')].map(b=>b._raw)"
SEL = "[...document.querySelectorAll('#blocks .block')].map((b,i)=>b.classList.contains('bsel')?i:null).filter(i=>i!==null)"
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page()
        pg.on("pageerror", lambda e: print("pageerror:", e))
        await pg.goto("file://" + __import__("os").path.abspath(__import__("os").path.join(__import__("os").path.dirname(__file__), "..", "index.html")) + ""); await pg.wait_for_timeout(300)
        await pg.click('[data-choice=browser]'); await pg.click('#newNote')
        await pg.evaluate("md=>{document.getElementById('toggleSrc').click();const t=document.getElementById('source');t.value=md;t.dispatchEvent(new Event('input'));document.getElementById('toggleSrc').click();}", '# T\n- a\n- b\n- c\npara')
        # mouse drag from block 1 to block 3
        b1 = await pg.locator('#blocks .block:nth-child(2)').bounding_box(); b3 = await pg.locator('#blocks .block:nth-child(4)').bounding_box()
        await pg.mouse.move(b1['x']+30, b1['y']+10); await pg.mouse.down(); await pg.mouse.move(b3['x']+30, b3['y']+10, steps=8); await pg.mouse.up(); await pg.wait_for_timeout(50)
        print("drag sel:", await pg.evaluate(SEL), "native sel empty:", await pg.evaluate("getSelection().toString()==''"))
        await pg.keyboard.press('Tab'); await pg.wait_for_timeout(30); print("tab:", await pg.evaluate(R), await pg.evaluate(SEL))
        await pg.keyboard.press('Shift+Tab'); await pg.wait_for_timeout(30); print("shift+tab:", await pg.evaluate(R))
        await pg.keyboard.press('Alt+Shift+ArrowDown'); await pg.wait_for_timeout(30); print("move down:", await pg.evaluate(R), await pg.evaluate(SEL))
        await pg.keyboard.press('Alt+Shift+ArrowUp'); await pg.wait_for_timeout(30); print("move up:", await pg.evaluate(R), await pg.evaluate(SEL))
        await pg.keyboard.press('Escape')
        # single line move
        await pg.click('#blocks .block:nth-child(1)'); await pg.keyboard.press('Alt+Shift+ArrowDown'); await pg.wait_for_timeout(30)
        print("single move:", await pg.evaluate(R), "editing:", await pg.evaluate("document.querySelector('.editing')?._raw"))
        await pg.keyboard.press('Control+z'); await pg.wait_for_timeout(30); print("undo:", await pg.evaluate(R))
        # shift+click extends
        await pg.click('#blocks .block:nth-child(2)'); await pg.click('#blocks .block:nth-child(4)', modifiers=['Shift']); await pg.wait_for_timeout(30)
        print("shift+click:", await pg.evaluate(SEL))
        await b.close()
asyncio.run(main())
