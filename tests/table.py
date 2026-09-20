import asyncio
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page()
        await pg.goto("file://" + __import__("os").path.abspath(__import__("os").path.join(__import__("os").path.dirname(__file__), "..", "index.html")) + ""); await pg.wait_for_timeout(300); await pg.click("[data-choice=browser]")
        bl = pg.locator('#blocks .block')
        print("sample table rendered:", await pg.evaluate("document.querySelectorAll('#blocks .b-table table').length"), await pg.evaluate("[...document.querySelectorAll('#blocks .b-table td')].map(t=>t.textContent)"))
        # new note, type a table
        await pg.click('#newNote'); await pg.wait_for_timeout(100)
        await pg.keyboard.type('| 名前 | 点数 |'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(50)
        print("after header Enter:", repr(await pg.evaluate("document.querySelector('#blocks .editing')._raw")))
        await pg.keyboard.type('田中 | 90 |'); await pg.keyboard.press('Enter'); await pg.keyboard.type('鈴木 | 85 |')
        await pg.keyboard.press('Enter'); await pg.wait_for_timeout(50)  # "| " row start
        await pg.keyboard.press('Backspace'); await pg.keyboard.press('Backspace')  # empty line
        await pg.keyboard.press('Enter'); await pg.wait_for_timeout(80)  # exit table
        print("blocks:", await bl.count(), "cls0:", await bl.nth(0).get_attribute('class'))
        print("formatted raw:\n" + await bl.nth(0).evaluate('e=>e._raw'))
        print("cells:", await pg.evaluate("[...document.querySelectorAll('#blocks td')].map(t=>t.textContent)"))
        # click a cell → caret at that cell
        cell = pg.locator('#blocks td').nth(3)
        await cell.click(); await pg.wait_for_timeout(50)
        print("caret:", await pg.evaluate("(()=>{const el=document.querySelector('.editing');const s=getSelection();const r=document.createRange();r.selectNodeContents(el);r.setEnd(s.anchorNode,s.anchorOffset);return JSON.stringify(el._raw.slice(r.toString().length, r.toString().length+2))})()"))
        await pg.keyboard.press('Tab'); await pg.wait_for_timeout(30)
        print("after Tab:", await pg.evaluate("(()=>{const el=document.querySelector('.editing');const s=getSelection();const r=document.createRange();r.selectNodeContents(el);r.setEnd(s.anchorNode,s.anchorOffset);return JSON.stringify(el._raw.slice(r.toString().length, r.toString().length+3))})()"))
        await pg.keyboard.press('Control+z'); await pg.wait_for_timeout(50)
        print("undo ok, blocks:", await bl.count())
        await b.close()
asyncio.run(main())
