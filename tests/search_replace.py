import asyncio
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page()
        pg.on("pageerror", lambda e: print("pageerror:", e))
        await pg.goto("file://" + __import__("os").path.abspath(__import__("os").path.join(__import__("os").path.dirname(__file__), "..", "index.html")) + ""); await pg.wait_for_timeout(300)
        await pg.click('[data-choice=browser]')
        # make a few notes
        for md in ['# 猫の日記\n\n今日は猫が3匹来た。cat cat', '# 犬の日記\n\n犬は来ない', '# 買い物\n\n- 猫缶\n- 犬用おやつ', '# メモ4\n\n猫', '# メモ5\n\nCAT']:
            await pg.click('#newNote'); await pg.evaluate("md=>{document.getElementById('toggleSrc').click();const t=document.getElementById('source');t.value=md;t.dispatchEvent(new Event('input'));document.getElementById('toggleSrc').click();}", md)
        await pg.wait_for_timeout(100)
        # global search
        await pg.fill('#gq', '猫'); await pg.wait_for_timeout(100)
        print("global:", await pg.evaluate("[...document.querySelectorAll('#list .item')].map(i=>i.querySelector('.n').textContent+' '+i.querySelector('.t').textContent+' | '+i.querySelector('.snip').innerText)"), await pg.evaluate("document.querySelector('#list .more')?.textContent"))
        await pg.click('#gre'); await pg.fill('#gq', '.'); await pg.wait_for_timeout(80)
        print("limited:", await pg.evaluate("document.querySelectorAll('#list .item').length"), await pg.evaluate("document.querySelector('#list .more')?.textContent"))
        await pg.click('#list .more'); await pg.wait_for_timeout(50)
        print("expanded:", await pg.evaluate("document.querySelectorAll('#list .item').length"), await pg.evaluate("document.querySelector('#list .more')?.textContent"))
        await pg.click('#gre')
        # regex + Aa
        await pg.fill('#gq', 'cat'); await pg.wait_for_timeout(50); print("cat ci:", await pg.evaluate("[...document.querySelectorAll('#list .n')].map(e=>e.textContent)"))
        await pg.click('#gcs'); await pg.wait_for_timeout(50); print("cat cs:", await pg.evaluate("[...document.querySelectorAll('#list .n')].map(e=>e.textContent)"))
        await pg.click('#gcs'); await pg.fill('#gq', '猫|犬'); await pg.wait_for_timeout(50); print("plain '猫|犬':", await pg.evaluate("document.querySelectorAll('#list .item').length"))
        await pg.click('#gre'); await pg.wait_for_timeout(50); print("regex '猫|犬':", await pg.evaluate("[...document.querySelectorAll('#list .item .n')].map(e=>e.textContent)"))
        await pg.fill('#gq', '('); await pg.wait_for_timeout(50); print("bad:", await pg.evaluate("document.querySelector('#list .empty')?.textContent"))
        # click result → note opens with find bar
        await pg.fill('#gq', '猫'); await pg.wait_for_timeout(50)
        await pg.click('#list .item .open'); await pg.wait_for_timeout(150)
        print("opened:", await pg.evaluate("document.getElementById('title').textContent"), "findbar:", not await pg.evaluate("document.getElementById('findbar').hidden"), "cnt:", await pg.evaluate("document.getElementById('fcnt').textContent"), "mark:", await pg.evaluate("document.querySelector(\"mark.fm\")?.textContent"))
        # in-note replace: open with Ctrl+H
        await pg.click('#blocks .block'); await pg.keyboard.press('Control+h'); await pg.wait_for_timeout(50)
        await pg.fill('#fq', '猫'); await pg.fill('#fr', 'ネコ'); await pg.wait_for_timeout(50)
        print("cnt:", await pg.evaluate("document.getElementById('fcnt').textContent"))
        await pg.keyboard.press('Enter'); await pg.wait_for_timeout(50)  # in fr → replaceOne? focus is on fr
        print("after replace one:", await pg.evaluate("document.getElementById('fcnt').textContent"), await pg.evaluate("[...document.querySelectorAll('#blocks .block')].map(b=>b._raw)"))
        await pg.click('#frepall'); await pg.wait_for_timeout(50)
        print("after all:", await pg.evaluate("[...document.querySelectorAll('#blocks .block')].map(b=>b._raw)"))
        await pg.keyboard.press('Control+z'); await pg.wait_for_timeout(50)
        print("undo all:", await pg.evaluate("[...document.querySelectorAll('#blocks .block')].map(b=>b._raw)"))
        # regex replace with $1
        await pg.fill('#fq', '(\\d)匹'); await pg.click('#fre'); await pg.fill('#fr', '$1頭'); await pg.click('#frepall'); await pg.wait_for_timeout(50)
        print("regex $1:", await pg.evaluate("document.querySelectorAll('#blocks .block')[2]._raw"))
        await b.close()
asyncio.run(main())
