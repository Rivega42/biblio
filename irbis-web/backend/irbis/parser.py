#!/usr/bin/env python3
"""Parse the IRBIS client record representation into structured fields/subfields.

Record (from READ 'C', data lines):
    <mfn>#<status>
    0#<version>
    2147483647#{GUID}          # optional system GUID field (tag = MaxInt32)
    <tag>#<value>              # value may contain ^X subfields
    ...
Subfield delimiter is '^' (confirmed in Prohod B).
"""

SYSTEM_GUID_TAG = '2147483647'


def parse_subfields(value: str):
    """Return (head_text, {code: text}). head_text = text before the first '^'."""
    if '^' not in value:
        return value, {}
    parts = value.split('^')
    head = parts[0]
    subs = {}
    for p in parts[1:]:
        if not p:
            continue
        code, text = p[0], p[1:]
        # repeatable subfield codes: keep first, expose list under code+'*' if needed
        if code in subs:
            subs.setdefault('_repeats', []).append({code: text})
        else:
            subs[code] = text
    return head, subs


def parse_record(data_lines):
    rec = {'mfn': None, 'status': None, 'version': None, 'guid': None, 'fields': []}
    seen_mfn = False
    seen_version = False
    for line in data_lines:
        if '#' not in line:
            continue
        tag, value = line.split('#', 1)
        if not seen_mfn:
            rec['mfn'] = int(tag) if tag.isdigit() else None
            rec['status'] = value
            seen_mfn = True
            continue
        if not seen_version and tag == '0':
            rec['version'] = value
            seen_version = True
            continue
        if tag == SYSTEM_GUID_TAG:
            rec['guid'] = value
            continue
        head, subs = parse_subfields(value)
        rec['fields'].append({'tag': tag, 'value': value, 'text': head, 'subfields': subs})
    return rec


def field(rec, tag):
    """First field value with given tag, or None."""
    for f in rec['fields']:
        if f['tag'] == tag:
            return f
    return None


def fields(rec, tag):
    return [f for f in rec['fields'] if f['tag'] == tag]
