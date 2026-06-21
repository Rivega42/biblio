#!/usr/bin/env python3
"""ИРБИС ``.mnu`` / ``.tre`` parsers (gap A5, epic #188).

These are the import side of the seeding engine — used when migrating an
institution's own dictionaries (``kv.mnu``, ``mhr.mnu``, ``spec.tre``) off a
source ИРБИС server (SPEC §4.2). The parsers themselves are pure and fully
unit-tested; the *live-server extraction* (pulling the files over the ИРБИС
protocol / from ``C:\\IRBIS\\DATA``) is a documented stub below — its only
external dependency is the connection, which is supplied from env, never the
repo.

Formats (recon #VOC-03):
  * ``.mnu`` — alternating lines: ``code`` then ``label``, repeated, terminated
    by a ``*****`` marker line. CP1251 on disk. A trailing empty pair (the
    artefact left before ``*****``) is skipped.
  * ``.tre`` — one node per line; leading dots encode depth (``.`` == 1 level).
    The node value follows the dots. ``parent`` is reconstructed by a level stack.
"""

MNU_TERMINATOR = '*****'


def decode_irbis(data):
    """Decode ИРБИС file bytes (CP1251 on disk) to ``str``.

    Accepts ``str`` unchanged (already-decoded input). Bytes are tried as CP1251
    first (the ИРБИС on-disk encoding) and fall back to UTF-8 for files that were
    already re-encoded, so both round-trip.
    """
    if isinstance(data, str):
        return data
    try:
        return data.decode('cp1251')
    except UnicodeDecodeError:
        return data.decode('utf-8', errors='replace')


def parse_mnu(data):
    """Parse an ИРБИS ``.mnu`` menu into ``[(code, label), ...]``.

    ``data`` may be ``bytes`` (CP1251) or ``str``. Parsing stops at the first
    ``*****`` terminator line. Lines are paired (code, label); a final pair whose
    code is empty (the ``*****`` artefact, recon #VOC-03) is dropped. A label with
    no following partner is paired with ``''``.
    """
    text = decode_irbis(data)
    # Normalise newlines; keep interior whitespace of labels but strip line ends.
    raw = [ln.strip('\r\n') for ln in text.split('\n')]
    lines = []
    for ln in raw:
        if ln.strip() == MNU_TERMINATOR:
            break
        lines.append(ln)
    # Drop a trailing wholly-empty line (artefact before the terminator).
    while lines and lines[-1].strip() == '':
        lines.pop()
    pairs = []
    i = 0
    while i < len(lines):
        code = lines[i].strip()
        label = lines[i + 1].strip() if i + 1 < len(lines) else ''
        i += 2
        if code == '':
            continue                       # skip empty-code artefact pair (#VOC-03)
        pairs.append((code, label))
    return pairs


def parse_tre(data):
    """Parse an ИРБИS ``.tre`` tree into a flat node list with parents.

    Returns ``[{'code', 'label', 'depth', 'parent'}, ...]`` in document order.
    Leading dots = depth (``.`` per level); the text after the dots is the node
    value (used as both code and label — recon does not split them for ``.tre``).
    ``parent`` is the index (into the returned list) of the nearest preceding node
    one level shallower, or ``None`` at the root.

    Blank lines and a ``*****`` terminator (if present) are ignored.
    """
    text = decode_irbis(data)
    nodes = []
    stack = []                              # stack[d] = index of last node at depth d
    for raw in text.split('\n'):
        ln = raw.strip('\r\n')
        if ln.strip() == MNU_TERMINATOR:
            break
        if ln.strip() == '':
            continue
        depth = 0
        while depth < len(ln) and ln[depth] == '.':
            depth += 1
        value = ln[depth:].strip()
        if value == '':
            continue
        idx = len(nodes)
        parent = stack[depth - 1] if depth > 0 and depth - 1 < len(stack) else None
        nodes.append({'code': value, 'label': value, 'depth': depth, 'parent': parent})
        # Truncate the stack to this depth and record us as the last node here.
        del stack[depth:]
        stack.append(idx)
    return nodes


def import_mnu_from_source(name, *, dsn=None):  # pragma: no cover - documented stub
    """STUB: pull dictionary ``name`` off a *source* ИРБИС server and parse it.

    The primary onboarding path (SPEC §2.3) auto-imports institution
    dictionaries from the ИРБИS the tenant is migrating off — by reading the
    ``.mnu`` file over the protocol (FILE command ``L`` / ``EXPORTMNU``) or from
    the server's data directory. Connection + credentials come from the onboarding
    env/config (``SOURCE_IRBIS_*``), NEVER from the repository.

    Not wired here: the live transport is out of scope for this slice. Once a
    connection is supplied, the bytes flow straight through ``parse_mnu`` above —
    which is the part that is implemented and tested. Raises to make the missing
    piece explicit.
    """
    raise NotImplementedError(
        'live source-ИРБИС extraction is a documented stub (SPEC §2.3); '
        'supply file bytes to parse_mnu()/parse_tre() instead. Source-server '
        'credentials come from SOURCE_IRBIS_* env, never the repo.')
