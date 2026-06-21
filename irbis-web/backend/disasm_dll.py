#!/usr/bin/env python3
"""READ-ONLY disassembly of selected IRBIS64.dll exports (capstone x86-32),
annotating call targets (export names) and string references. Decompilation-lite."""
import sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

DLL = r'C:\IRBIS64\IRBIS64.dll'
TARGETS = ['Irbis_Format', 'UNIFOR', 'IrbisFindPosting', 'Irbis_InitPFT']
MAXINS = 90

pe = pefile.PE(DLL)
base = pe.OPTIONAL_HEADER.ImageBase
exp = {}
for e in pe.DIRECTORY_ENTRY_EXPORT.symbols:
    if e.name:
        exp[e.address] = e.name.decode('latin-1')      # rva -> name


def read_str(rva):
    try:
        d = pe.get_data(rva, 80)
    except Exception:
        return None
    # ascii
    a = bytes(d).split(b'\x00')[0]
    if len(a) >= 3 and all(32 <= c < 127 for c in a):
        return a.decode('latin-1')
    # utf-16le
    try:
        w = bytes(d)
        end = w.find(b'\x00\x00')
        s = w[:end].decode('utf-16le')
        if len(s) >= 3 and all(31 < ord(c) < 0x500 for c in s):
            return s
    except Exception:
        pass
    return None


md = Cs(CS_ARCH_X86, CS_MODE_32)
data = pe.__data__
for t in TARGETS:
    rva = next((r for r, n in exp.items() if n == t), None)
    if rva is None:
        print('\n=== %s: NOT exported ===' % t)
        continue
    off = pe.get_offset_from_rva(rva)
    code = data[off:off + 1200]
    print('\n=== %s  (rva %#x) ===' % (t, rva))
    n = 0
    for ins in md.disasm(bytes(code), base + rva):
        ann = ''
        ops = ins.op_str
        if ins.mnemonic in ('call', 'jmp') and ops.startswith('0x'):
            tgt = int(ops, 16) - base
            if tgt in exp:
                ann = '   ; -> %s()' % exp[tgt]
        for tok in ops.replace('[', ' ').replace(']', ' ').split():
            if tok.startswith('0x') and len(tok) >= 8:
                s = read_str(int(tok, 16) - base)
                if s:
                    ann = '   ; "%s"' % s[:48]
                    break
        print('  %08x  %-6s %s%s' % (ins.address, ins.mnemonic, ops, ann))
        n += 1
        if (ins.mnemonic == 'ret' and n > 4) or n >= MAXINS:
            break
