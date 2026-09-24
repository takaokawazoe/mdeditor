# shared helpers for the tests
# Setting a note's text used to go through the #source textarea. The raw view replaced it,
# so the text now goes in the way a person would: select every line, then paste over it.
async def set_md(pg, md):
    await pg.evaluate("t=>navigator.clipboard.writeText(t)", md)
    await pg.click('#blocks .block')
    await pg.keyboard.press('Control+a')
    await pg.keyboard.press('Control+v')
    await pg.wait_for_timeout(150)
CUR_MD = """(() => { const d = JSON.parse(localStorage.getItem('wysimd.v1') || '{}');
  const n = (d.notes || []).find(x => x.id === d.currentId) || (d.notes || [])[0];
  return n ? n.blocks.join('\\n') : ''; })()"""
async def get_md(pg):  # the current note's markdown, as saved (the DOM may show tables with padded columns)
    return await pg.evaluate(CUR_MD)
CUR_FILE = """(() => { const d = JSON.parse(localStorage.getItem('wysimd.v1') || '{}');
  const n = (d.notes || []).find(x => x.id === d.currentId); return n ? n.file : null; })()"""
CUR_FS_MTIME = """(() => { const d = JSON.parse(localStorage.getItem('wysimd.v1') || '{}');
  const n = (d.notes || []).find(x => x.id === d.currentId); return n ? n.fsMtime : 0; })()"""
