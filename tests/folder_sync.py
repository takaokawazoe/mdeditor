import asyncio
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); ctx = await b.new_context(); pg = await ctx.new_page()
        pg.on("pageerror", lambda e: print("pageerror:", e))
        # emulate the directory picker with the origin-private file system (same handle API)
        await pg.add_init_script("window.showDirectoryPicker = async () => { const r = await navigator.storage.getDirectory(); const d = await r.getDirectoryHandle('memo', {create:true}); Object.defineProperty(d,'name',{value:'memo'}); return d; };")
        await pg.goto("http://localhost:8123/index.html"); await pg.wait_for_timeout(400); await pg.click('[data-choice=later]')
        print("fs box:", await pg.evaluate("document.getElementById('fs').innerText.slice(0,40)"))
        await pg.click('#fs [data-act=switch]'); await pg.click('#fsDlg [data-dlg=ok]'); await pg.wait_for_timeout(1200)
        ls = "(async()=>{const r=await navigator.storage.getDirectory();const d=await r.getDirectoryHandle('memo');const o=[];for await(const [n,h] of d.entries()){o.push(n+':'+(await (await h.getFile()).text()).length)}return o})()"
        print("files after connect:", await pg.evaluate(ls))
        # type into a new note → file created; then change title → renamed
        await pg.click('#newNote'); await pg.keyboard.type('# 買い物'); await pg.wait_for_timeout(1300)
        print("after new note:", await pg.evaluate(ls))
        await pg.keyboard.type('リスト'); await pg.wait_for_timeout(1300)
        print("after rename:", await pg.evaluate(ls))
        # external file appears → reload picks it up
        await pg.evaluate("(async()=>{const r=await navigator.storage.getDirectory();const d=await r.getDirectoryHandle('memo');const fh=await d.getFileHandle('外部.md',{create:true});const w=await fh.createWritable();await w.write('# 外部で作ったメモ\\n\\n本文');await w.close()})()")
        await pg.click('#fs [data-act=reload]'); await pg.wait_for_timeout(500)
        print("list:", await pg.evaluate("[...document.querySelectorAll('#list .t')].map(e=>e.textContent)"))
        # reload page → reconnect silently (permission granted for OPFS)
        await pg.reload(); await pg.wait_for_timeout(1000)
        print("after reload fs box:", await pg.evaluate("document.getElementById('fs').innerText.slice(0,30)"))
        print("notes with file:", await pg.evaluate("JSON.parse(localStorage.getItem('wysimd.v1')).notes.map(n=>n.file)"))
        # delete the shopping note → file removed
        await pg.evaluate("document.querySelector('#list .item .x').dispatchEvent(new MouseEvent('click',{bubbles:true}))")
        await pg.click('#list [data-act=del]'); await pg.wait_for_timeout(400)
        print("after delete:", await pg.evaluate(ls))
        await b.close()
asyncio.run(main())
