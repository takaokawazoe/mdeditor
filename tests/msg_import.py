import asyncio, os, struct, tempfile
from playwright.async_api import async_playwright
import mkmsg
# dropping an Outlook .msg adds the mail as a note (Compound File: one stream per property)
errors = []
def check(label, got, want=True):
    ok = got == want
    print(('OK  ' if ok else 'NG  ') + label + ('' if ok else '  -> got ' + repr(got) + ' want ' + repr(want)))
    if not ok: errors.append(label)
MD = "[...document.querySelectorAll('#blocks .block')].map(e=>e._raw).join('\\n')"
P, U = mkmsg.prop, mkmsg.u16
FILETIME = (1790000000 + 11644473600) * 10**7  # a fixed moment in 2026
def plain_msg():
    return mkmsg.build([
        P('0037', '001F', U('打ち合わせのお願い')),
        P('1000', '001F', U('お世話になります。\r\n\r\n明日14時でいかがでしょうか。\r\n\r\n> 前のメールの引用')),
        P('0C1A', '001F', U('山田太郎')),
        P('0C1F', '001F', U('yamada@example.com')),
        P('0E04', '001F', U('鈴木花子')),
    ], )
def dated_msg():
    return mkmsg.build([
        P('0037', '001F', U('日付つき')), P('1000', '001F', U('本文')),
        ('__properties_version1.0', mkmsg.props_stream([(0x00390040, FILETIME)])),
    ])
def html_msg():
    html = '<html><body><h1>見出し</h1><p>1行目<br>2行目</p>&amp;</body></html>'.encode('utf-8')
    return mkmsg.build([
        P('0037', '001F', U('HTMLだけのメール')),
        P('1013', '0102', html),
        ('__properties_version1.0', mkmsg.props_stream([(0x3FDE0003, 65001)])),
    ])
def cp932_msg():
    return mkmsg.build([
        P('0037', '001E', '古い形式の件名'.encode('cp932')),
        P('1000', '001E', '本文もShift_JISです'.encode('cp932')),
        ('__properties_version1.0', mkmsg.props_stream([(0x3FDE0003, 932)])),
    ])
def rtf_only_msg():
    return mkmsg.build([P('0037', '001F', U('RTFだけ')), P('1009', '0102', b'\x00' * 40)])
def attach_msg():
    return mkmsg.build([P('0037', '001F', U('添付つき')), P('1000', '001F', U('本文だけ読む'))],
                       [('__attach_version1.0_#00000000', [P('3707', '001F', U('資料.pdf'))])])
def big_msg():  # a body over the 4096-byte mini-stream cutoff goes through the normal sectors
    return mkmsg.build([P('0037', '001F', U('長い本文')), P('1000', '001F', U('あ' * 5000))])
async def main():
    tmp = tempfile.mkdtemp()
    files = {'plain': plain_msg(), 'dated': dated_msg(), 'html': html_msg(), 'cp932': cp932_msg(),
             'rtf': rtf_only_msg(), 'attach': attach_msg(), 'big': big_msg()}
    paths = {}
    for k, data in files.items():
        p = os.path.join(tmp, k + '.msg'); open(p, 'wb').write(data); paths[k] = p
    async with async_playwright() as pw:
        b = await pw.chromium.launch(); pg = await b.new_page()
        pg.on("pageerror", lambda e: errors.append('pageerror: ' + str(e)) or print("PAGEERROR", e))
        await pg.goto("file://" + os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "index.html"))); await pg.wait_for_timeout(300)
        await pg.click('[data-choice=browser]')
        async def open_msg(key):
            await pg.set_input_files('#fileInput', [paths[key]]); await pg.wait_for_timeout(400)
            return await pg.evaluate(MD)

        md = await open_msg('plain')
        check('subject becomes the title', md.splitlines()[0], '# 打ち合わせのお願い')
        check('sender name and address', '差出人：山田太郎 <yamada@example.com>' in md, True)
        check('recipient', '宛先：鈴木花子' in md, True)
        check('body is read', '明日14時でいかがでしょうか。' in md, True)
        check('quoted lines survive', '> 前のメールの引用' in md, True)

        md = await open_msg('dated')
        check('the sent time is read', '日時：2026' in md, True)

        md = await open_msg('html')
        check('html body is stripped to text', '見出し' in md and '1行目' in md and '2行目' in md, True)
        check('entities are decoded', md.rstrip().endswith('&'), True)

        md = await open_msg('cp932')
        check('Shift_JIS subject', md.splitlines()[0], '# 古い形式の件名')
        check('Shift_JIS body', '本文もShift_JISです' in md, True)

        md = await open_msg('rtf')
        check('an RTF-only body says so', 'RTF形式のため取り出せませんでした' in md, True)

        md = await open_msg('attach')
        check('attachment body still read', '本文だけ読む' in md, True)
        check('attachment name is listed', '添付：資料.pdf' in md, True)

        md = await open_msg('big')
        check('a long body (past the mini-stream cutoff) is read whole', md.count('あ'), 5000)

        # a file that is not a compound file is refused, not imported as junk
        bad = os.path.join(tmp, 'bad.msg'); open(bad, 'wb').write(b'not a compound file at all')
        before = await pg.evaluate("document.querySelectorAll('#list .item').length")
        await pg.set_input_files('#fileInput', [bad]); await pg.wait_for_timeout(400)
        check('a broken .msg adds nothing', await pg.evaluate("document.querySelectorAll('#list .item').length"), before)
        check('and says so', 'メールファイルとして読めませんでした' in await pg.inner_text('#toast'), True)
        await b.close()
    print('\nFAILED:', errors if errors else 'none')
asyncio.run(main())
