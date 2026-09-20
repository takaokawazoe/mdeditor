"""backup: one-shot export/import, .zip round trip, and folder-vs-browser conflicts."""
# No server needed: the folder is a fake handle injected before the app script runs,
# so file mtimes are ours to set and every case below is deterministic.
import asyncio, os
from playwright.async_api import async_playwright

URL = "file://" + os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "index.html"))

# a File System Access directory handle backed by a plain Map, with mtimes we control
FAKE_FS = """
(() => {
  const enc = new TextEncoder();
  function fileHandle(map, name) {
    return {
      kind: 'file', name,
      getFile: async () => { const r = map.get(name); return { name, type: 'text/markdown', lastModified: r.mtime, text: async () => r.text, arrayBuffer: async () => enc.encode(r.text).buffer }; },
      createWritable: async () => { let buf = ''; return { write: async d => { buf += d; }, close: async () => { map.set(name, { text: buf, mtime: Date.now() }); } }; },
    };
  }
  function makeDir(name, map) {
    return {
      kind: 'directory', name, __map: map,
      queryPermission: async () => 'granted',
      requestPermission: async () => 'granted',
      async *entries() { for (const k of [...map.keys()]) yield [k, fileHandle(map, k)]; },
      getFileHandle: async (n, o) => { if (!map.has(n)) { if (!o || !o.create) throw Object.assign(new Error('nf'), { name: 'NotFoundError' }); map.set(n, { text: '', mtime: Date.now() }); } return fileHandle(map, n); },
      removeEntry: async n => { map.delete(n); },
    };
  }
  const main = makeDir('テストフォルダ', new Map());
  window.__fs = { main, files: main.__map, makeDir, next: null };
  window.showDirectoryPicker = async () => { const d = window.__fs.next || main; window.__fs.next = null; return d; };
})();
"""

# the app's own zip writer, so the test feeds it exactly what it produces
MAKE_ZIP = """
(names) => {
  const enc = new TextEncoder();
  const tab = (() => { const t = new Uint32Array(256); for (let i = 0; i < 256; i++) { let c = i; for (let k = 0; k < 8; k++) c = (c & 1) ? (0xEDB88320 ^ (c >>> 1)) : (c >>> 1); t[i] = c >>> 0; } return t; })();
  const crc32 = b => { let c = 0xFFFFFFFF; for (let i = 0; i < b.length; i++) c = tab[(c ^ b[i]) & 0xFF] ^ (c >>> 8); return (c ^ 0xFFFFFFFF) >>> 0; };
  const local = [], central = []; let off = 0;
  for (const n of names) {
    const nm = enc.encode(n + '.md'), data = enc.encode('# ' + n + '\\n\\n' + n + ' の本文'), crc = crc32(data);
    const lh = new DataView(new ArrayBuffer(30));
    lh.setUint32(0, 0x04034b50, true); lh.setUint16(4, 20, true); lh.setUint16(6, 0x0800, true);
    lh.setUint32(14, crc, true); lh.setUint32(18, data.length, true); lh.setUint32(22, data.length, true);
    lh.setUint16(26, nm.length, true);
    local.push(new Uint8Array(lh.buffer), nm, data);
    const ch = new DataView(new ArrayBuffer(46));
    ch.setUint32(0, 0x02014b50, true); ch.setUint16(4, 20, true); ch.setUint16(6, 20, true); ch.setUint16(8, 0x0800, true);
    ch.setUint32(16, crc, true); ch.setUint32(20, data.length, true); ch.setUint32(24, data.length, true);
    ch.setUint16(28, nm.length, true); ch.setUint32(42, off, true);
    central.push(new Uint8Array(ch.buffer), nm);
    off += 30 + nm.length + data.length;
  }
  const cd = central.reduce((s, a) => s + a.length, 0);
  const eo = new DataView(new ArrayBuffer(22));
  eo.setUint32(0, 0x06054b50, true); eo.setUint16(8, names.length, true); eo.setUint16(10, names.length, true);
  eo.setUint32(12, cd, true); eo.setUint32(16, off, true);
  const blob = new Blob([...local, ...central, new Uint8Array(eo.buffer)], { type: 'application/zip' });
  const dt = new DataTransfer();
  dt.items.add(new File([blob], 'backup.zip', { type: 'application/zip' }));
  document.dispatchEvent(new DragEvent('drop', { dataTransfer: dt, bubbles: true, cancelable: true }));
}
"""

TITLES = "[...document.querySelectorAll('#list .t')].map(e=>e.textContent.replace('🔒',''))"
SRC = "document.getElementById('source').value"
TOAST = "document.getElementById('toast').textContent"

errors = []
def check(name, cond, detail=''):
    print(('OK  ' if cond else 'NG  ') + name + ('' if cond else '  -> ' + str(detail)))
    if not cond: errors.append(name)

async def set_src(pg, md):
    await pg.evaluate("md=>{document.getElementById('toggleSrc').click();const t=document.getElementById('source');t.value=md;t.dispatchEvent(new Event('input'));document.getElementById('toggleSrc').click();}", md)

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); ctx = await b.new_context(); pg = await ctx.new_page()
        pg.on("pageerror", lambda e: errors.append('pageerror: ' + str(e)) or print("PAGEERROR", e))
        await pg.add_init_script(FAKE_FS)
        await pg.goto(URL); await pg.wait_for_timeout(400)

        ids = await pg.evaluate("[...document.querySelectorAll('#fileMenu .btn:not([hidden])')].map(b=>b.id)")
        check('file menu items present', all(a in ids for a in ['openFile', 'openZip', 'openDir', 'download', 'exportDir', 'exportZip']), ids)

        await pg.click('[data-choice=folder]'); await pg.wait_for_timeout(1400)
        check('folder connected and notes written', await pg.evaluate("__fs.files.size") >= 1, await pg.evaluate("[...__fs.files.keys()]"))

        # --- conflict: the folder copy is newer -> it wins, the browser text survives as a copy
        md0 = await pg.evaluate(SRC)
        key = await pg.evaluate("md=>[...__fs.files.entries()].find(([k,v])=>v.text===md)?.[0]", md0)
        check('current note is on disk', bool(key), await pg.evaluate("[...__fs.files.keys()]"))
        await set_src(pg, md0 + '\n\nブラウザ側の追記'); await pg.wait_for_timeout(80)
        await pg.evaluate("k=>__fs.files.set(k,{text:'# フォルダで書き換えた\\n\\n外から',mtime:Date.now()+1})", key)
        await pg.click('#fs [data-act=reload]'); await pg.wait_for_timeout(900)
        check('folder version adopted', (await pg.evaluate(SRC)).startswith('# フォルダで書き換えた'), (await pg.evaluate(SRC))[:40])
        check('browser side kept as a copy', any('ブラウザ側の写し' in t for t in await pg.evaluate(TITLES)), await pg.evaluate(TITLES))
        keep = await pg.evaluate("document.querySelector('#list .item.active')?.dataset.id")
        await pg.click("#list .item:has(.t:text-matches('ブラウザ側の写し')) .open"); await pg.wait_for_timeout(200)
        check('the copy holds the browser text', 'ブラウザ側の追記' in await pg.evaluate(SRC), (await pg.evaluate(SRC))[:60])
        await pg.click('#list .item[data-id="' + keep + '"] .open'); await pg.wait_for_timeout(1400)

        # --- conflict: the browser copy is newer -> it wins and is written back, the folder text survives
        md1 = await pg.evaluate(SRC)
        key = await pg.evaluate("md=>[...__fs.files.entries()].find(([k,v])=>v.text===md)?.[0]", md1)
        await pg.wait_for_timeout(300)
        await set_src(pg, md1 + '\n\n後から追記'); await pg.wait_for_timeout(80)
        await pg.evaluate("k=>__fs.files.set(k,{text:'# 少し古いフォルダ版',mtime:Date.now()-150})", key)
        await pg.click('#fs [data-act=reload]'); await pg.wait_for_timeout(1400)
        check('browser version kept', '後から追記' in await pg.evaluate(SRC), (await pg.evaluate(SRC))[-30:])
        check('folder side kept as a copy', any('フォルダ側の写し' in t for t in await pg.evaluate(TITLES)), await pg.evaluate(TITLES))
        check('browser version written back', await pg.evaluate("[...__fs.files.values()].some(v=>v.text.includes('後から追記'))"))

        # --- .zip import, then the same .zip again
        await pg.evaluate(MAKE_ZIP, ['控えA', '控えB']); await pg.wait_for_timeout(900)
        t = await pg.evaluate(TITLES)
        check('zip import added both notes', len([x for x in t if x in ('控えA', '控えB')]) == 2, t)
        before = len(t)
        await pg.evaluate("document.getElementById('toast').textContent=''")
        await pg.evaluate(MAKE_ZIP, ['控えA', '控えB']); await pg.wait_for_timeout(900)
        check('re-importing the same zip adds nothing', len(await pg.evaluate(TITLES)) == before, [before, await pg.evaluate(TITLES), await pg.evaluate(TOAST)])

        # --- one-shot export: writes everything, keeps the current connection
        await pg.wait_for_timeout(1200)
        await pg.evaluate("window.__out = new Map(); __fs.next = __fs.makeDir('書き出し先', __out);")
        await pg.click('#fileBtn'); await pg.click('#exportDir'); await pg.wait_for_timeout(1200)
        got, want = await pg.evaluate("__out.size"), len(await pg.evaluate(TITLES))
        check('exportToFolder wrote every note', got == want, [got, want, await pg.evaluate("[...__out.keys()]")])
        check('exportToFolder file names are unique', await pg.evaluate("new Set([...__out.keys()].map(k=>k.toLowerCase())).size === __out.size"))
        check('exportToFolder did not switch the connection', await pg.evaluate("document.querySelector('#fs .nm').textContent") == 'ローカルPC（テストフォルダ）')

        # --- one-shot import: adds the folder's .md, keeps the current connection
        await pg.evaluate("__fs.next = __fs.makeDir('読み込み元', new Map([['新規1.md',{text:'# 新規1\\n\\nx',mtime:Date.now()}],['新規2.md',{text:'# 新規2\\n\\ny',mtime:Date.now()}]]))")
        await pg.click('#fileBtn'); await pg.click('#openDir'); await pg.wait_for_timeout(1200)
        t = await pg.evaluate(TITLES)
        check('importFromFolder added both notes', '新規1' in t and '新規2' in t, t)
        check('importFromFolder did not switch the connection', await pg.evaluate("document.querySelector('#fs .nm').textContent") == 'ローカルPC（テストフォルダ）')

        await b.close()
    print('\nFAILED:', errors if errors else 'none')

asyncio.run(main())
