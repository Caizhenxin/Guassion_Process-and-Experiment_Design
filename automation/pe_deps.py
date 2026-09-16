# -*- coding: utf-8 -*-
"""pe_deps.py — 解析 PE (mexw64) 的静态 + 延迟导入表，并对照系统查找缺失 DLL。"""
import sys, struct, os, ctypes

def pe_imports(path):
    with open(path, 'rb') as f:
        data = f.read()
    if data[:2] != b'MZ':
        raise ValueError('not PE')
    pe_off = struct.unpack_from('<I', data, 0x3C)[0]
    assert data[pe_off:pe_off+4] == b'PE\0\0'
    coff = pe_off + 4
    nsec = struct.unpack_from('<H', data, coff+2)[0]
    opt_off = coff + 20
    magic = struct.unpack_from('<H', data, opt_off)[0]
    is64 = magic == 0x20B
    if not is64:
        raise ValueError('not 64-bit')
    dd_off = opt_off + 112
    # data dirs: [0]export [1]import [2]resource [3]exception [4]security
    # [5]basereloc [6]debug [7]arch [8]globalptr [9]tls [10]loadconfig
    # [11]boundimport [12]iat [13]delayimport [14]clr [15]reserved
    def dd(idx):
        off = dd_off + idx*8
        return struct.unpack_from('<II', data, off)
    # sections for RVA->offset
    secs = []
    sec_off = opt_off + (240 if is64 else 224)
    for i in range(nsec):
        s = sec_off + i*40
        name = data[s:s+8].rstrip(b'\0').decode('ascii', 'ignore')
        vsz, va, rawsz, raw = struct.unpack_from('<IIII', data, s+8)
        secs.append((va, raw, rawsz))
    def rva2off(rva):
        for va, raw, rawsz in secs:
            if va <= rva < va + rawsz:
                return raw + (rva - va)
        return None
    def cstr(off):
        if off is None:
            return None
        end = data.find(b'\0', off)
        return data[off:end].decode('ascii', 'ignore')
    imports = {}
    imp_rva, imp_sz = dd(1)
    off = rva2off(imp_rva)
    if off is not None:
        while True:
            name_rva = struct.unpack_from('<I', data, off+12)[0]
            if name_rva == 0:
                break
            dll = cstr(rva2off(name_rva))
            if dll:
                imports[dll] = imports.get(dll, 0) + 1
            off += 20
    delay = {}
    d_rva, d_sz = dd(13)
    if d_rva:
        off = rva2off(d_rva)
        if off is not None:
            for _ in range(d_sz // 32):
                name_rva = struct.unpack_from('<I', data, off+4)[0]
                if name_rva == 0:
                    break
                dll = cstr(rva2off(name_rva))
                if dll:
                    delay[dll] = delay.get(dll, 0) + 1
                off += 32
    return imports, delay

def find_on_system(name):
    sys32 = os.path.join(os.environ.get('SystemRoot', r'C:\Windows'), 'System32')
    cand = [
        os.path.join(sys32, name),
        r'E:\matlab2023b\bin\win64' + '\\' + name,
    ]
    for c in cand:
        if os.path.exists(c):
            return c
    return None

for p in sys.argv[1:]:
    print('==== %s ====' % os.path.basename(p))
    try:
        imp, delay = pe_imports(p)
    except Exception as e:
        print('parse error:', e); continue
    print('-- static imports --')
    for d in sorted(imp):
        loc = find_on_system(d)
        print('  %-32s %s' % (d, ('OK  ' + loc) if loc else '*** MISSING ***'))
    if delay:
        print('-- delay imports --')
        for d in sorted(delay):
            loc = find_on_system(d)
            print('  %-32s %s' % (d, ('OK  ' + loc) if loc else '*** MISSING ***'))
