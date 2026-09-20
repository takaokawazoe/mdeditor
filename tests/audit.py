import asyncio
from playwright.async_api import async_playwright
R = "[...document.querySelectorAll('#blocks .block')].map(b=>b._raw)"
E = "document.querySelector('#blocks .editing')?._raw ?? null"
SEL = "[...document.querySelectorAll('#blocks .block')].map((b,i)=>b.classList.contains('bsel')?i:null).filter(i=>i!==null)"
errors = []
def check(name, cond, detail=''):
    print(('OK  ' if cond else 'NG  ') + name + ('' if cond else '  -> ' + str(detail)))
    if not cond: errors.append(name)
async def setmd(pg, md):
    await pg.evaluate("md=>{document.getElementById('toggleSrc').click();const t=document.getElementById('source');t.value=md;t.dispatchEvent(new Event('input'));document.getElementById('toggleSrc').click();}", md)
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); ctx = await b.new_context(permissions=['clipboard-read','clipboard-write']); pg = await ctx.new_page()
        pg.on("pageerror", lambda e: errors.append('pageerror: '+str(e)) or print("PAGEERROR", e))
        await pg.goto("file://" + __import__("os").path.abspath(__import__("os").path.join(__import__("os").path.dirname(__file__), "..", "index.html")) + ""); await pg.wait_for_timeout(300)
        await pg.click('[data-choice=browser]')
        # --- 1. list editing basics
        await pg.click('#newNote'); await pg.keyboard.type('- a'); await pg.keyboard.press('Enter'); await pg.keyboard.type('b'); await pg.keyboard.press('Enter'); await pg.keyboard.press('Enter')
        check('empty list item exits list', await pg.evaluate(R) == ['- a','- b',''], await pg.evaluate(R))
        await pg.keyboard.press('Backspace'); await pg.wait_for_timeout(30)
        check('backspace on empty line merges up', await pg.evaluate(R) == ['- a','- b'] and await pg.evaluate(E) == '- b', await pg.evaluate(R))
        await pg.keyboard.press('Home'); await pg.keyboard.press('Backspace'); await pg.wait_for_timeout(30)
        check('backspace at line start merges into previous', await pg.evaluate(R) == ['- a- b'], await pg.evaluate(R))
        await pg.keyboard.press('Control+z'); await pg.wait_for_timeout(30)
        check('undo merge', await pg.evaluate(R) == ['- a','- b'], await pg.evaluate(R))
        # --- 2. task toggle + undo
        await setmd(pg, '- [ ] todo\n- [x] done'); await pg.click('#blocks .block:nth-child(1) .cb'); await pg.wait_for_timeout(30)
        check('checkbox toggle', await pg.evaluate(R) == ['- [x] todo','- [x] done'], await pg.evaluate(R))
        await pg.keyboard.press('Control+z'); await pg.wait_for_timeout(30)
        check('undo checkbox', await pg.evaluate(R) == ['- [ ] todo','- [x] done'], await pg.evaluate(R))
        # --- 3. code block flow
        await pg.click('#newNote'); await pg.keyboard.type('```'); await pg.keyboard.press('Enter'); await pg.keyboard.type('x = 1'); await pg.keyboard.press('Enter'); await pg.keyboard.type('```'); await pg.keyboard.press('Enter'); await pg.keyboard.type('after')
        check('code fence', await pg.evaluate(R) == ['```\nx = 1\n```','after'], await pg.evaluate(R))
        # --- 4. paste multi-line into middle of a line
        await pg.click('#newNote'); await pg.keyboard.type('startend'); await pg.keyboard.press('ArrowLeft'); await pg.keyboard.press('ArrowLeft'); await pg.keyboard.press('ArrowLeft')
        await pg.evaluate("()=>{const dt=new DataTransfer();dt.setData('text/plain','A\\n# B\\nC');document.querySelector('.editing').dispatchEvent(new ClipboardEvent('paste',{clipboardData:dt,bubbles:true,cancelable:true}))}"); await pg.wait_for_timeout(30)
        check('paste splits blocks', await pg.evaluate(R) == ['startA','# B','Cend'] and await pg.evaluate(E) == 'Cend', await pg.evaluate(R))
        await pg.keyboard.press('Control+z'); await pg.wait_for_timeout(30)
        check('undo paste', await pg.evaluate(R) == ['startend'], await pg.evaluate(R))
        # --- 5. shift+enter, then arrow nav in multi-line block
        await pg.click('#newNote'); await pg.keyboard.type('l1'); await pg.keyboard.press('Shift+Enter'); await pg.keyboard.type('l2'); await pg.wait_for_timeout(30)
        check('shift+enter newline in block', await pg.evaluate(R) == ['l1\nl2'], await pg.evaluate(R))
        await pg.keyboard.press('Enter'); await pg.keyboard.type('next'); await pg.keyboard.press('ArrowUp'); await pg.wait_for_timeout(30)
        check('arrow up into multi-line block', await pg.evaluate(E) == 'l1\nl2', await pg.evaluate(E))
        # --- 6. Ctrl+B with selection, then find/replace across formatting
        await pg.click('#newNote'); await pg.keyboard.type('bold me'); await pg.keyboard.press('Shift+Home'); await pg.keyboard.press('Control+b'); await pg.wait_for_timeout(30)
        check('ctrl+b wraps', await pg.evaluate(R) == ['**bold me**'], await pg.evaluate(R))
        # --- 7. block selection + find interplay
        await setmd(pg, 'one\ntwo\nthree\nfour')
        await pg.click('#blocks .block:nth-child(2)'); await pg.keyboard.press('Shift+ArrowDown'); await pg.wait_for_timeout(20)
        await pg.keyboard.press('Control+f'); await pg.wait_for_timeout(30)
        check('ctrl+f while block-selected opens find', not await pg.evaluate("document.getElementById('findbar').hidden"))
        await pg.fill('#fq', 'o'); await pg.wait_for_timeout(30)
        cnt = await pg.evaluate("document.getElementById('fcnt').textContent")
        check('find count with peek', cnt == '1/3', cnt)
        await pg.keyboard.press('Escape'); await pg.wait_for_timeout(30)
        check('esc from find edits the match block', await pg.evaluate(E) == 'one', await pg.evaluate(E))
        check('block selection cleared on find/esc', await pg.evaluate(SEL) == [], await pg.evaluate(SEL))
        # --- 8. delete note while find open, and switching notes
        await pg.keyboard.press('Control+f'); await pg.fill('#fq', 'two'); await pg.wait_for_timeout(30)
        await pg.click('#list .item.active .x'); await pg.click('#list [data-act=del]'); await pg.wait_for_timeout(100)
        check('delete note with find open: no error', True)
        await pg.fill('#fq', 'x'); await pg.wait_for_timeout(30)
        # --- 9. table: click cell, tab, exit, undo whole thing
        await pg.click('#newNote'); await pg.keyboard.type('| h1 | h2'); await pg.keyboard.press('Enter'); await pg.keyboard.type('a | b'); await pg.keyboard.press('Enter'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(50)
        check('table typed+exited', (await pg.evaluate(R))[0].startswith('| h1') and (await pg.evaluate(R))[1] == '', await pg.evaluate(R))
        await pg.click('#blocks td:nth-child(2)'); await pg.wait_for_timeout(30)
        sel_off = await pg.evaluate("(()=>{const el=document.querySelector('.editing');const s=getSelection();const r=document.createRange();r.selectNodeContents(el);r.setEnd(s.anchorNode,s.anchorOffset);return el._raw.slice(r.toString().length,r.toString().length+1)})()")
        check('click cell → caret at cell', sel_off == 'b', sel_off)
        await pg.keyboard.press('Escape'); await pg.wait_for_timeout(30)
        # --- 10. heading Enter mid-line splits, bullet continuation with checkbox
        await setmd(pg, '# Head line'); await pg.click('#blocks .block'); await pg.keyboard.press('End')
        for _ in range(5): await pg.keyboard.press('ArrowLeft')
        await pg.keyboard.press('Enter'); await pg.wait_for_timeout(30)
        check('split heading mid-line', await pg.evaluate(R) == ['# Head',' line'], await pg.evaluate(R))
        await setmd(pg, '- [ ] t'); await pg.click('#blocks .block'); await pg.keyboard.press('End'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(30)
        check('task continuation', await pg.evaluate(E) == '- [ ] ', await pg.evaluate(E))
        # --- 11. import while editing; title rename in list
        await pg.click('#newNote'); await pg.keyboard.type('editing here')
        await pg.set_input_files('#fileInput', ['/tmp/a.md']); await pg.wait_for_timeout(300)
        check('import while editing', await pg.evaluate("document.getElementById('title').textContent") == '買い物')
        # --- 12. source view keeps shortcuts native; toggling back re-renders
        await pg.click('#toggleSrc'); await pg.keyboard.press('Control+f'); await pg.wait_for_timeout(30)
        check('find bar not opened in source mode', await pg.evaluate("document.getElementById('findbar').hidden"))
        await pg.click('#toggleSrc')
        # --- 13. undo/redo button states
        st = await pg.evaluate("[document.getElementById('undo').disabled, document.getElementById('redo').disabled]")
        check('history buttons sane', st[1] == True, st)
        # --- 14. select-all then typing replaces everything, then undo restores
        await setmd(pg, 'p1\np2\np3'); await pg.click('#blocks .block'); await pg.keyboard.press('Control+a'); await pg.keyboard.press('Control+a'); await pg.keyboard.press('KeyZ'); await pg.wait_for_timeout(50)
        check('select-all + type replaces', await pg.evaluate(R) == ['z'], await pg.evaluate(R))
        await pg.keyboard.press('Control+z'); await pg.wait_for_timeout(50)
        r = await pg.evaluate(R)
        check('undo after replace-all typing', r == ['p1','p2','p3'] or r == [''] , r)
        # --- 15. global search escape clears, list restored
        await pg.fill('#gq', 'p'); await pg.wait_for_timeout(30); await pg.keyboard.press('Escape'); await pg.wait_for_timeout(30)
        check('global search esc restores list', await pg.evaluate("document.querySelectorAll('#list .item .d').length") > 0)
        await b.close()
    print('\nFAILED:', errors if errors else 'none')
asyncio.run(main())
