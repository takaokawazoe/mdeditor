import asyncio, os, tempfile
from playwright.async_api import async_playwright
from mkeml import eml_plain, eml_jis, eml_multipart, eml_html_only, eml_attach
# dropping a .eml adds the mail as a note: subject as the title, then sender/date, then the body
errors = []
def check(label, got, want=True):
    ok = got == want
    print(('OK  ' if ok else 'NG  ') + label + ('' if ok else '  -> got ' + repr(got) + ' want ' + repr(want)))
    if not ok: errors.append(label)
MD = "[...document.querySelectorAll('#blocks .block')].map(e=>e._raw).join('\\n')"
TITLES = "[...document.querySelectorAll('#list .t')].map(e=>e.textContent.replace('🔒',''))"
async def main():
    tmp = tempfile.mkdtemp()
    paths = {}
    for name, maker, enc in [('plain', eml_plain, 'utf-8'), ('jis', eml_jis, 'ascii'), ('multi', eml_multipart, 'utf-8'),
                             ('html', eml_html_only, 'utf-8'), ('attach', eml_attach, 'utf-8')]:
        p = os.path.join(tmp, name + '.eml')
        open(p, 'w', encoding=enc, newline='').write(maker())
        paths[name] = p
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page()
        pg.on("pageerror", lambda e: errors.append('pageerror: ' + str(e)) or print("PAGEERROR", e))
        await pg.goto("file://" + os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "index.html"))); await pg.wait_for_timeout(300)
        await pg.click('[data-choice=browser]')
        async def open_eml(key):
            await pg.set_input_files('#fileInput', [paths[key]]); await pg.wait_for_timeout(400)
            return await pg.evaluate(MD)

        md = await open_eml('plain')
        check('subject becomes the title', md.splitlines()[0], '# 打ち合わせの件')
        check('sender is kept', '差出人：Yamada <yamada@example.com>' in md, True)
        check('recipient is kept', '宛先：Suzuki <suzuki@example.com>' in md, True)
        check('date is kept', '日時：Mon, 28 Sep 2026 10:00:00 +0900' in md, True)
        check('base64 body is decoded', '明日の打ち合わせは14時からです。' in md, True)
        check('quoted lines survive as markdown quotes', '> 前のメールの引用' in md, True)
        check('the note is listed by its subject', '打ち合わせの件' in await pg.evaluate(TITLES), True)

        md = await open_eml('jis')
        check('ISO-2022-JP subject', md.splitlines()[0], '# 古いメール')
        check('quoted-printable + ISO-2022-JP body', '件名も本文もISO-2022-JPです。' in md, True)

        md = await open_eml('multi')
        check('multipart prefers the plain part', 'プレーンの本文' in md and 'HTMLの本文' not in md, True)

        md = await open_eml('html')
        check('html-only mail is stripped to text', '見出し' in md and '1行目' in md and '2行目' in md, True)
        check('entities are decoded', '& と <タグ>' in md, True)
        check('style blocks are dropped', 'color:red' not in md, True)

        md = await open_eml('attach')
        check('attachment body still read', '本文だけ読む' in md, True)
        check('attachment names are listed', '添付：資料.pdf' in md, True)

        # the same mail twice adds nothing
        before = len(await pg.evaluate(TITLES))
        await open_eml('plain')
        check('the same mail is not added twice', len(await pg.evaluate(TITLES)), before)
        await b.close()
    print('\nFAILED:', errors if errors else 'none')
asyncio.run(main())
