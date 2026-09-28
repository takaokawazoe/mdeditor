"""Builds a minimal .msg (Compound File Binary Format) so the importer can be tested
without shipping a real mail. Sectors are 512 bytes, streams under 4096 bytes go into
the mini stream, exactly as Outlook writes them."""
import struct
SSZ, MSZ, CUTOFF = 512, 64, 4096
FREE, EOC = 0xFFFFFFFF, 0xFFFFFFFE
def _pad(b, n):
    return b + b'\0' * (-len(b) % n)
def _chain(fat, first, count):  # link `count` sectors starting at `first`
    for i in range(count - 1):
        fat.append(first + i + 1)
    fat.append(EOC)
    return first
def build(streams, storages=()):
    """streams: list of (name, bytes) at the root. storages: list of (name, [(name, bytes), ...])"""
    entries = [('Root Entry', 5, None)]
    for name, data in streams:
        entries.append((name, 2, data))
    for sname, subs in storages:
        entries.append((sname, 1, None))
        for name, data in subs:
            entries.append((name, 2, data))
    mini_parts, big_parts = [], []
    layout = {}
    for i, (name, kind, data) in enumerate(entries):
        if kind != 2:
            continue
        if len(data) < CUTOFF:
            start = sum(len(_pad(d, MSZ)) for d in mini_parts) // MSZ
            mini_parts.append(data); layout[i] = ('mini', start, len(data))
        else:
            big_parts.append((i, data))
    mini = b''.join(_pad(d, MSZ) for d in mini_parts)
    # sector plan: [FAT][directory][mini FAT][mini stream][big streams...]
    dir_count = max(1, (len(entries) * 128 + SSZ - 1) // SSZ)
    mini_fat_entries = len(mini) // MSZ
    mini_fat_count = max(1, (mini_fat_entries * 4 + SSZ - 1) // SSZ)
    mini_sectors = (len(mini) + SSZ - 1) // SSZ
    big_sizes = [( i, (len(d) + SSZ - 1) // SSZ, d) for i, d in big_parts]
    fat = []
    dir_start = 1
    _chain(fat, dir_start, dir_count) if False else None
    # build the FAT by walking the plan
    fat = [EOC]                      # sector 0: the FAT itself
    pos = 1
    dir_start = pos; fat += [pos + i + 1 for i in range(dir_count - 1)] + [EOC]; pos += dir_count
    mini_fat_start = pos; fat += [pos + i + 1 for i in range(mini_fat_count - 1)] + [EOC]; pos += mini_fat_count
    mini_start = pos if mini_sectors else EOC
    if mini_sectors:
        fat += [pos + i + 1 for i in range(mini_sectors - 1)] + [EOC]; pos += mini_sectors
    for i, n, d in big_sizes:
        layout[i] = ('big', pos, len(d))
        fat += [pos + k + 1 for k in range(n - 1)] + [EOC]; pos += n
    fat += [FREE] * ((SSZ // 4) - len(fat) % (SSZ // 4) if len(fat) % (SSZ // 4) else 0)
    # mini FAT: every mini stream is a straight chain
    mfat = []
    at = 0
    for d in mini_parts:
        n = max(1, (len(d) + MSZ - 1) // MSZ)
        mfat += [at + k + 1 for k in range(n - 1)] + [EOC]
        at += n
    mfat += [FREE] * ((SSZ // 4) * mini_fat_count - len(mfat))
    # directory
    dirbuf = b''
    for i, (name, kind, data) in enumerate(entries):
        nm = name.encode('utf-16-le') + b'\0\0'
        e = bytearray(128)
        e[0:len(nm)] = nm
        struct.pack_into('<H', e, 0x40, len(nm))
        e[0x42] = kind
        e[0x43] = 1  # black
        struct.pack_into('<III', e, 0x44, FREE, FREE, FREE)
        if kind == 5:
            struct.pack_into('<I', e, 0x4C, 1 if len(entries) > 1 else FREE)  # child = first entry after root
            struct.pack_into('<I', e, 0x74, mini_start if mini_sectors else EOC)
            struct.pack_into('<I', e, 0x78, len(mini))
        elif kind == 2:
            where, start, size = layout[i]
            struct.pack_into('<I', e, 0x74, start)
            struct.pack_into('<I', e, 0x78, size)
        dirbuf += bytes(e)
    out = bytearray()
    hdr = bytearray(SSZ)
    hdr[0:8] = bytes([0xD0, 0xCF, 0x11, 0xE0, 0xA1, 0xB1, 0x1A, 0xE1])
    struct.pack_into('<H', hdr, 0x18, 0x003E); struct.pack_into('<H', hdr, 0x1A, 3)
    struct.pack_into('<H', hdr, 0x1C, 0xFFFE)
    struct.pack_into('<H', hdr, 0x1E, 9)      # 512-byte sectors
    struct.pack_into('<H', hdr, 0x20, 6)      # 64-byte mini sectors
    struct.pack_into('<I', hdr, 0x2C, 1)      # one FAT sector
    struct.pack_into('<I', hdr, 0x30, dir_start)
    struct.pack_into('<I', hdr, 0x38, CUTOFF)
    struct.pack_into('<I', hdr, 0x3C, mini_fat_start)
    struct.pack_into('<I', hdr, 0x40, mini_fat_count)
    struct.pack_into('<I', hdr, 0x44, EOC)
    struct.pack_into('<I', hdr, 0x4C, 0)      # the FAT lives in sector 0
    for i in range(1, 109):
        struct.pack_into('<I', hdr, 0x4C + i * 4, FREE)
    out += hdr
    out += _pad(struct.pack('<%dI' % len(fat), *fat), SSZ)
    out += _pad(dirbuf, SSZ)
    out += _pad(struct.pack('<%dI' % len(mfat), *mfat), SSZ)
    out += _pad(mini, SSZ)
    for i, n, d in big_sizes:
        out += _pad(d, SSZ)
    return bytes(out)
def prop(tag_id, type_hex, value):
    return ('__substg1.0_%s%s' % (tag_id, type_hex), value)
def u16(s):
    return s.encode('utf-16-le')
def props_stream(pairs):  # fixed-size properties: 8-byte header per entry after a 32-byte preamble
    buf = bytearray(32)
    for tag, value in pairs:
        buf += struct.pack('<IIQ', tag, 6, value)
    return bytes(buf)
