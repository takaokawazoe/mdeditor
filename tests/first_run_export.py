import asyncio
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        # 1) first run, choose browser; download via blob
        ctx = await b.new_context(accept_downloads=True); pg = await ctx.new_page()
        pg.on("pageerror", lambda e: print("pageerror:", e))
        await pg.goto("http://localhost:8123/index.html"); await pg.wait_for_timeout(500)
        print("dialog shown:", not await pg.evaluate("document.getElementById('setup').hidden"))
        await pg.click('[data-choice=browser]'); await pg.wait_for_timeout(100)
        print("stored:", await pg.evaluate("!!localStorage.getItem('wysimd.v1')"))
        async with pg.expect_download() as dl:
            await pg.click('#fileBtn'); await pg.click('#download')
        d = await dl.value; print("downloaded:", d.suggested_filename)
        await pg.reload(); await pg.wait_for_timeout(500)
        print("dialog on 2nd load:", not await pg.evaluate("document.getElementById('setup').hidden"))
        await ctx.close()
        # 2) first run, choose folder that already has a note → sample dropped
        ctx = await b.new_context(); pg = await ctx.new_page()
        await pg.add_init_script("window.showDirectoryPicker = async () => { const r = await navigator.storage.getDirectory(); const d = await r.getDirectoryHandle('m2', {create:true}); Object.defineProperty(d,'name',{value:'m2'}); return d; };")
        await pg.goto("http://localhost:8123/index.html"); await pg.wait_for_timeout(300)
        await pg.evaluate("(async()=>{const r=await navigator.storage.getDirectory();const d=await r.getDirectoryHandle('m2',{create:true});const fh=await d.getFileHandle('既存.md',{create:true});const w=await fh.createWritable();await w.write('# 既存のメモ');await w.close()})()")
        await pg.click('[data-choice=folder]'); await pg.wait_for_timeout(1200)
        print("list after folder choice:", await pg.evaluate("[...document.querySelectorAll('#list .t')].map(e=>e.textContent)"))
        print("fs box:", await pg.evaluate("document.getElementById('fs').innerText.slice(0,20)"))
        await ctx.close()
        # 3) first run, empty folder → sample kept and written
        ctx = await b.new_context(); pg = await ctx.new_page()
        await pg.add_init_script("window.showDirectoryPicker = async () => { const r = await navigator.storage.getDirectory(); const d = await r.getDirectoryHandle('m3', {create:true}); Object.defineProperty(d,'name',{value:'m3'}); return d; };")
        await pg.goto("http://localhost:8123/index.html"); await pg.wait_for_timeout(300)
        await pg.click('[data-choice=folder]'); await pg.wait_for_timeout(1200)
        print("empty folder →", await pg.evaluate("(async()=>{const r=await navigator.storage.getDirectory();const d=await r.getDirectoryHandle('m3');const o=[];for await(const [n] of d.entries())o.push(n);return o})()"))
        await b.close()
asyncio.run(main())
