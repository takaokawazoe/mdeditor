import asyncio
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); ctx = await b.new_context(permissions=['clipboard-read','clipboard-write']); pg = await ctx.new_page()
        pg.on("pageerror", lambda e: print("pageerror:", e))
        await pg.goto("file://" + __import__("os").path.abspath(__import__("os").path.join(__import__("os").path.dirname(__file__), "..", "index.html")) + ""); await pg.wait_for_timeout(300)
        await pg.click('[data-choice=browser]'); await pg.click('#newNote')
        await pg.evaluate("md=>{document.getElementById('toggleSrc').click();const t=document.getElementById('source');t.value=md;t.dispatchEvent(new Event('input'));document.getElementById('toggleSrc').click();}", '# 見出し\n\n- a\n- b\n- c\n\n段落')
        raws = "[...document.querySelectorAll('#blocks .block')].map(b=>b._raw)"
        sel = "[...document.querySelectorAll('#blocks .block')].map((b,i)=>b.classList.contains('bsel')?i:null).filter(i=>i!==null)"
        await pg.click('#blocks .block:nth-child(3)'); await pg.keyboard.press('End')
        await pg.keyboard.press('Shift+ArrowDown'); await pg.wait_for_timeout(30); print("shift+down:", await pg.evaluate(sel), "editing:", await pg.evaluate("!!document.querySelector('.editing')"))
        await pg.keyboard.press('Shift+ArrowDown'); await pg.wait_for_timeout(30); print("again:", await pg.evaluate(sel))
        await pg.keyboard.press('Shift+ArrowUp'); await pg.wait_for_timeout(30); print("shift+up:", await pg.evaluate(sel))
        await pg.keyboard.press('Control+c'); await pg.wait_for_timeout(100); print("clipboard:", repr(await pg.evaluate("navigator.clipboard.readText()")))
        await pg.keyboard.press('Escape'); await pg.wait_for_timeout(30); print("esc → editing:", await pg.evaluate("document.querySelector('.editing')?._raw"), await pg.evaluate(sel))
        await pg.keyboard.press('Shift+ArrowUp'); await pg.wait_for_timeout(30)  # first line? caret at end of "- b"... at first line of block → selects b and a
        print("up from b:", await pg.evaluate(sel))
        await pg.keyboard.press('Backspace'); await pg.wait_for_timeout(50); print("deleted:", await pg.evaluate(raws), "editing:", await pg.evaluate("document.querySelector('.editing')?._raw"))
        await pg.keyboard.press('Control+z'); await pg.wait_for_timeout(50); print("undo:", await pg.evaluate(raws))
        # type-over
        await pg.click('#blocks .block:nth-child(1)'); await pg.keyboard.press('Shift+ArrowDown'); await pg.keyboard.press('Shift+ArrowDown'); await pg.wait_for_timeout(30)
        await pg.keyboard.type('新'); await pg.wait_for_timeout(80); print("type-over:", await pg.evaluate(raws))
        # ctrl+a twice
        await pg.keyboard.press('Control+a'); await pg.keyboard.press('Control+a'); await pg.wait_for_timeout(30); print("select all:", await pg.evaluate(sel))
        await pg.keyboard.press('Delete'); await pg.wait_for_timeout(50); print("delete all:", await pg.evaluate(raws))
        await b.close()
asyncio.run(main())
