import asyncio
from playwright.async_api import async_playwright
# file menu, sidebar hide, Ctrl+A, Alt+Shift+←→, storage panel + switch / reconnect dialogs
# needs `python3 -m http.server 8123` (the folder picker is emulated with OPFS, like folder_sync.py)
URL = "http://localhost:8123/index.html"
PICKER = """
window.showDirectoryPicker = async () => { const r = await navigator.storage.getDirectory(); const d = await r.getDirectoryHandle('とても長い名前のメモ保存用フォルダ2026', {create:true}); return d; };
if (sessionStorage.getItem('askPerm')) { FileSystemHandle.prototype.queryPermission = async () => 'prompt'; FileSystemHandle.prototype.requestPermission = async () => 'granted'; }
"""
errors = []
def check(label, cond, extra=''):
    print(('OK  ' if cond else 'NG  ') + label + ('' if cond else '  -> ' + str(extra)))
    if not cond: errors.append(label)
RAWS = "[...document.querySelectorAll('#blocks .block')].map(e=>e._raw)"
SEL = "[...document.querySelectorAll('#blocks .block')].map((e,i)=>e.classList.contains('bsel')?i:-1).filter(i=>i>=0)"
async def setmd(pg, md):
    await pg.click('#newNote')
    await pg.evaluate("md=>{document.getElementById('toggleSrc').click();const t=document.getElementById('source');t.value=md;t.dispatchEvent(new Event('input'));document.getElementById('toggleSrc').click();}", md)
async def idle(pg):  # no line open, nothing selected, focus on the page body
    if await pg.evaluate("!!document.querySelector('#blocks .bsel')"): await pg.keyboard.press('Escape')
    await pg.click('#title'); await pg.wait_for_timeout(50)
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={'width': 1200, 'height': 800}); pg = await ctx.new_page()
        pg.on("pageerror", lambda e: errors.append('pageerror: ' + str(e)) or print("PAGEERROR", e))
        await pg.add_init_script(PICKER)
        await pg.goto(URL); await pg.wait_for_timeout(400); await pg.click('[data-choice=browser]')

        # --- file menu
        check('menu closed at start', not await pg.is_visible('#fileMenu'))
        await pg.click('#fileBtn')
        items = await pg.evaluate("[...document.querySelectorAll('#fileMenu .btn')].filter(b=>b.offsetParent).map(b=>b.textContent)")
        check('menu items', items == ['指定したファイルを開く', '.zip内のすべての.mdを開く', 'フォルダ内のすべての.mdを開く', 'このファイルを.mdで保存', 'フォルダへ書き出し', '.zipで保存'], items)
        await pg.keyboard.press('Escape'); check('Esc closes the menu', not await pg.is_visible('#fileMenu'))
        await pg.click('#fileBtn'); await pg.click('#editor', position={'x': 600, 'y': 600}); check('outside click closes the menu', not await pg.is_visible('#fileMenu'))
        check('zip input accepts only .zip', await pg.evaluate("document.getElementById('zipInput').accept") == '.zip,application/zip')
        async with pg.expect_file_chooser() as fc:
            await pg.click('#fileBtn'); await pg.click('#openZip')
        check('.zip item opens a chooser for .zip', (await fc.value).element is not None)
        check('copy button hidden on wide screens', not await pg.is_visible('#copy'))
        check('no old backup box in sidebar', await pg.evaluate("!document.querySelector('#fs .bk')"))

        # --- sidebar hide / show
        check('sidebar button is ＜ while open', await pg.inner_text('#menu') == '＜', await pg.inner_text('#menu'))
        await pg.click('#menu'); check('it hides the sidebar', not await pg.is_visible('#side'))
        check('button becomes ＞ once hidden', await pg.inner_text('#menu') == '＞', await pg.inner_text('#menu'))
        await pg.reload(); await pg.wait_for_timeout(300); check('hidden state is remembered', not await pg.is_visible('#side'))
        await pg.keyboard.press('Control+Backslash'); check('Ctrl+\\ shows it again', await pg.is_visible('#side'))
        check('button back to ＜', await pg.inner_text('#menu') == '＜', await pg.inner_text('#menu'))
        await pg.keyboard.press('Control+Backslash'); await pg.keyboard.press('Control+Shift+F'); await pg.wait_for_timeout(50)
        check('Ctrl+Shift+F brings the sidebar back', await pg.is_visible('#gq'))
        await pg.keyboard.press('Escape')

        # --- Ctrl+A: one press selects every line
        await setmd(pg, '# T\n- a\n- b\npara')
        await pg.click('#blocks .block:nth-child(3)'); await pg.keyboard.press('Control+a')
        check('Ctrl+A while editing selects all lines at once', await pg.evaluate(SEL) == [0, 1, 2, 3], await pg.evaluate(SEL))
        await idle(pg)
        check('no line open', await pg.evaluate("!document.querySelector('#blocks .editing') && !document.querySelector('#blocks .bsel')"))
        await pg.keyboard.press('Control+a')
        check('Ctrl+A with no line open selects all lines', await pg.evaluate(SEL) == [0, 1, 2, 3], await pg.evaluate(SEL))

        # --- Alt+Shift+→/← indent the selection
        await pg.click('#blocks .block:nth-child(2)'); await pg.keyboard.press('Shift+ArrowDown')
        check('two lines selected', await pg.evaluate(SEL) == [1, 2], await pg.evaluate(SEL))
        await pg.keyboard.press('Alt+Shift+ArrowRight')
        check('Alt+Shift+→ indents', (await pg.evaluate(RAWS))[1:3] == ['  - a', '  - b'], await pg.evaluate(RAWS))
        check('selection kept after indent', await pg.evaluate(SEL) == [1, 2], await pg.evaluate(SEL))
        await pg.keyboard.press('Alt+Shift+ArrowLeft')
        check('Alt+Shift+← outdents', (await pg.evaluate(RAWS))[1:3] == ['- a', '- b'], await pg.evaluate(RAWS))

        # --- locked note: Ctrl+A selects, but Backspace does not delete
        await idle(pg); await pg.click('#lockBtn'); await idle(pg)
        await pg.keyboard.press('Control+a'); await pg.keyboard.press('Backspace'); await pg.wait_for_timeout(50)
        check('locked note survives Ctrl+A, Backspace', len(await pg.evaluate(RAWS)) == 4, await pg.evaluate(RAWS))
        await pg.keyboard.press('Escape'); await pg.click('#lockBtn')

        # --- storage panel: browser -> folder -> browser
        fs_text = "document.getElementById('fs').innerText.replace(/\\s+/g,' ').trim()"
        check('browser mode label', 'ブラウザ（ローカルストレージ）' in await pg.evaluate(fs_text), await pg.evaluate(fs_text))
        await pg.click('#fs [data-act=switch]')
        check('to-folder dialog', 'ローカルPCのフォルダを選択してください' in await pg.inner_text('#fsDlgMsg'), await pg.inner_text('#fsDlgMsg'))
        check('to-folder buttons', [await pg.inner_text('#fsDlg [data-dlg=ok]'), await pg.inner_text('#fsDlg [data-dlg=cancel]')] == ['フォルダを選択', 'キャンセル'])
        await pg.click('#fsDlg [data-dlg=cancel]'); check('cancel closes, still browser', await pg.evaluate("document.getElementById('fsDlg').hidden") and 'ブラウザ' in await pg.evaluate(fs_text))
        await pg.click('#fs [data-act=switch]'); await pg.click('#fsDlg [data-dlg=ok]'); await pg.wait_for_timeout(1200)
        t = await pg.evaluate(fs_text)
        check('folder mode label, long name shortened', 'ローカルPC（とても長い名前のメモ保存用フォルダ…）' in t, t)
        check('full name in tooltip', await pg.evaluate("document.querySelector('#fs .name').title") == 'とても長い名前のメモ保存用フォルダ2026')
        check('reload button kept', await pg.is_visible('#fs [data-act=reload]'))
        await pg.click('#fs [data-act=switch]')
        check('to-browser dialog', 'ブラウザ（ローカルストレージ）に保存します' in await pg.inner_text('#fsDlgMsg'), await pg.inner_text('#fsDlgMsg'))
        check('to-browser buttons', [await pg.inner_text('#fsDlg [data-dlg=ok]'), await pg.inner_text('#fsDlg [data-dlg=cancel]')] == ['切り替える', 'キャンセル'])
        await pg.click('#fsDlg [data-dlg=cancel]'); check('cancel keeps the folder', 'ローカルPC' in await pg.evaluate(fs_text))

        # --- reconnect prompt on the next load
        await pg.evaluate("sessionStorage.setItem('askPerm','1')"); await pg.reload(); await pg.wait_for_timeout(600)
        check('reconnect dialog on load', not await pg.evaluate("document.getElementById('fsDlg').hidden") and await pg.inner_text('#fsDlgTitle') == 'フォルダに再接続してください')
        check('reconnect buttons', [await pg.inner_text('#fsDlg [data-dlg=ok]'), await pg.inner_text('#fsDlg [data-dlg=cancel]')] == ['接続する', 'あとで'])
        await pg.click('#fsDlg [data-dlg=cancel]')
        t = await pg.evaluate(fs_text); check('later -> panel says not connected', '未接続' in t and await pg.is_visible('#fs [data-act=reconnect]'), t)
        await pg.click('#fs [data-act=reconnect]'); await pg.wait_for_timeout(1000)
        t = await pg.evaluate(fs_text); check('reconnected from the panel', '未接続' not in t and 'ローカルPC' in t, t)
        await pg.click('#fs [data-act=switch]'); await pg.click('#fsDlg [data-dlg=ok]'); await pg.wait_for_timeout(300)
        check('switched back to browser', 'ブラウザ（ローカルストレージ）' in await pg.evaluate(fs_text), await pg.evaluate(fs_text))
        await pg.reload(); await pg.wait_for_timeout(500)
        check('no reconnect prompt after switching to browser', await pg.evaluate("document.getElementById('fsDlg').hidden"))
        await ctx.close()

        # --- no folder API (Firefox/Safari): no switch button, no folder items
        ctx = await b.new_context(viewport={'width': 1200, 'height': 800}); pg = await ctx.new_page()
        await pg.add_init_script("delete window.showDirectoryPicker")
        await pg.goto(URL); await pg.wait_for_timeout(400)
        check('no switch button without folder API', not await pg.is_visible('#fs [data-act=switch]'))
        await pg.click('#fileBtn')
        items = await pg.evaluate("[...document.querySelectorAll('#fileMenu .btn')].filter(b=>b.offsetParent).map(b=>b.id)")
        check('folder items hidden without folder API', items == ['openFile', 'openZip', 'download', 'exportZip'], items)
        await ctx.close()

        # --- phone: everything in the … menu, copy shown as 「すべてをコピー」
        ctx = await b.new_context(viewport={'width': 390, 'height': 700}, has_touch=True, is_mobile=True); pg = await ctx.new_page()
        await pg.goto(URL); await pg.wait_for_timeout(400); await pg.tap('[data-choice=browser]')
        await pg.tap('#moreBtn'); await pg.wait_for_timeout(100)
        vis = await pg.evaluate("[...document.querySelectorAll('#moreMenu .btn')].filter(b=>b.offsetParent).map(b=>b.textContent)")
        check('phone menu lists file items + copy', 'すべてをコピー' in vis and '.zipで保存' in vis and 'ファイル ▾' not in vis, vis)
        await pg.tap('#copy'); await pg.wait_for_timeout(200)
        check('copy toast', 'コピー' in await pg.inner_text('#toast'), await pg.inner_text('#toast'))
        await pg.tap('#menu'); await pg.wait_for_timeout(300)
        check('☰ still opens the drawer on phones', await pg.evaluate("document.getElementById('side').classList.contains('open')"))
        check('phone keeps the ☰ icon', await pg.inner_text('#menu') == '☰', await pg.inner_text('#menu'))
        await b.close()
    print('\nFAILED:', errors if errors else 'none')
asyncio.run(main())
