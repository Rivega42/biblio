#!/usr/bin/env python3
"""READ-ONLY RE probe of the IRBIS DLLs: exports (API), imports, sections, and
'speaking' strings (format/prefix/error/SQL/protocol hints). No modification."""
import sys, re
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass
import pefile

DLLS = [r'C:\IRBIS64\irbis64_client.dll', r'C:\IRBIS64\IRBIS64.dll']

KEEP = re.compile(
    r'\.(pft|mnu|tre|fst|gbl|wss|ini|par)\b|(?<![A-Za-z])[A-Z]{1,4}=|'
    r'\bselect\b|\binsert\b|\bupdate\b|ERROR|ОШИБ|ИРБИС|IRBIS|формат|FORMAT|'
    r'RECORD|\bMFN\b|TERM|SEARCH|UNIFOR|RUSMARC|MARC|Z39|\bRDR\b|\bRQST\b',
    re.I)


def strings(data, minlen=5):
    for m in re.finditer((b'[\x20-\x7e]{%d,}' % minlen), data):
        yield m.group().decode('latin-1', 'replace')
    for m in re.finditer((b'(?:[\x20-\x7e]\x00){%d,}' % minlen), data):
        yield m.group().decode('utf-16le', 'replace')


for path in DLLS:
    print('\n===== %s =====' % path)
    pe = pefile.PE(path, fast_load=True)
    pe.parse_data_directories([
        pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_EXPORT'],
        pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT']])
    print('machine=%x subsystem=%d sections=%s' % (
        pe.FILE_HEADER.Machine, pe.OPTIONAL_HEADER.Subsystem,
        [s.Name.decode('latin-1').strip('\x00') for s in pe.sections]))
    exp = []
    if hasattr(pe, 'DIRECTORY_ENTRY_EXPORT'):
        for e in pe.DIRECTORY_ENTRY_EXPORT.symbols:
            if e.name:
                exp.append(e.name.decode('latin-1'))
    print('EXPORTS (%d):' % len(exp))
    for x in exp[:120]:
        print('   ', x)
    imp = []
    if hasattr(pe, 'DIRECTORY_ENTRY_IMPORT'):
        for d in pe.DIRECTORY_ENTRY_IMPORT:
            imp.append(d.dll.decode('latin-1'))
    print('IMPORTS:', imp)
    data = open(path, 'rb').read()
    seen = set(); keep = []
    for s in strings(data):
        s = s.strip()
        if not s or s in seen:
            continue
        seen.add(s)
        if KEEP.search(s):
            keep.append(s)
    print('INTERESTING STRINGS (%d of %d unique):' % (len(keep), len(seen)))
    for x in keep[:150]:
        print('   ', x[:140])
