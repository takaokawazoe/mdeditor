import asyncio, os
from playwright.async_api import async_playwright
# phone-sized page with real touch input (CDP) — long-press to lift, drag, release
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={'width': 390, 'height': 700}, has_touch=True, is_mobile=True)
        pg = await ctx.new_page(); cdp = await ctx.new_cdp_session(pg)
        pg.on("pageerror", lambda e: print("pageerror:", e))
        await pg.goto("file://" + os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "index.html"))); await pg.wait_for_timeout(300)
        await pg.tap('[data-choice=browser]')
        for t in ['A', 'B', 'C']:
            await pg.evaluate("document.getElementById('newNote').click()"); await pg.keyboard.type('# ' + t); await pg.wait_for_timeout(50)
        await pg.evaluate("document.activeElement.blur()"); await pg.wait_for_timeout(50)
        await pg.tap('#menu'); await pg.wait_for_timeout(300)
        titles = "[...document.querySelectorAll('#list .item .t')].map(e=>e.textContent)"
        cur = "document.getElementById('title').textContent"
        async def touch(kind, x=0, y=0):
            await cdp.send('Input.dispatchTouchEvent', {'type': kind, 'touchPoints': [] if kind == 'touchEnd' else [{'x': x, 'y': y}]})
        async def box(n):
            return await pg.locator(f'#list .item:nth-child({n}) .open').bounding_box()
        print("initial:", await pg.evaluate(titles), await pg.evaluate(cur))
        ok = True
        def check(label, cond):
            nonlocal ok; ok &= bool(cond); print(("OK  " if cond else "NG  ") + label)
        # 1) long-press C (1st), drag below A (3rd)
        s, d = await box(1), await box(3)
        x = s['x'] + 60
        await touch('touchStart', x, s['y'] + 15); await pg.wait_for_timeout(550)
        check("lifted after long-press", await pg.evaluate("!!document.querySelector('#list .item.dragging')"))
        for i in range(1, 11):
            await touch('touchMove', x, s['y'] + 15 + (d['y'] + d['height'] - 6 - s['y'] - 15) * i / 10); await pg.wait_for_timeout(16)
        check("drop marker shown", await pg.evaluate("!!document.querySelector('#list .item.drop-after')"))
        await touch('touchEnd'); await pg.wait_for_timeout(150)
        after = await pg.evaluate(titles)
        print("after drag:", after)
        check("order B,A,C", after[:3] == ['B', 'A', 'C'])
        check("drag did not open a note / close the drawer", await pg.evaluate("document.getElementById('side').classList.contains('open')"))
        check("markers cleared", await pg.evaluate("!document.querySelector('#list .dragging,#list .drop-before,#list .drop-after,#list.touch-dragging')"))
        # 2) quick swipe (move before timer) is a scroll, not a drag
        s = await box(1)
        await touch('touchStart', x, s['y'] + 15)
        for i in range(1, 6): await touch('touchMove', x, s['y'] + 15 + i * 12); await pg.wait_for_timeout(16)
        await pg.wait_for_timeout(500)
        check("swipe does not lift", await pg.evaluate("!document.querySelector('#list .item.dragging')"))
        await touch('touchEnd'); await pg.wait_for_timeout(100)
        check("order unchanged by swipe", (await pg.evaluate(titles))[:3] == ['B', 'A', 'C'])
        # 3) plain tap still opens the note
        await pg.tap('#list .item:nth-child(2) .open'); await pg.wait_for_timeout(300)
        check("tap opens note A", await pg.evaluate(cur) == 'A')
        # 4) persisted
        await pg.reload(); await pg.wait_for_timeout(300)
        check("order persisted", (await pg.evaluate(titles))[:3] == ['B', 'A', 'C'])
        # 5) holding near the bottom edge auto-scrolls a long list
        await pg.evaluate("for (let i = 0; i < 25; i++) document.getElementById('newNote').click()"); await pg.wait_for_timeout(200)
        await pg.evaluate("document.activeElement.blur()")
        if not await pg.evaluate("document.getElementById('side').classList.contains('open')"): await pg.tap('#menu'); await pg.wait_for_timeout(300)
        lr = await pg.locator('#list').bounding_box(); s = await box(1)
        await touch('touchStart', x, s['y'] + 15); await pg.wait_for_timeout(550)
        await touch('touchMove', x, s['y'] + 40); await touch('touchMove', x, lr['y'] + lr['height'] - 10); await pg.wait_for_timeout(600)
        check("auto-scroll near bottom edge", await pg.evaluate("document.getElementById('list').scrollTop") > 50)
        await touch('touchEnd'); await pg.wait_for_timeout(100)
        print("FAILED:", "none" if ok else "see NG")
        await b.close()
asyncio.run(main())
