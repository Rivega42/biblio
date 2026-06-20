#!/usr/bin/env python3
# Prohod B: empirical IRBIS64 wire-protocol probe (read-only).
# KEY finding from run 1-2: IRBIS uses ONE TCP CONNECTION PER REQUEST
# (server closes after each response); the session persists via client_id.
# Framing: "<bodyLen>\n" + body; lines separated by \n on send, \r\n on receive.
import socket, sys, os, random

HOST = sys.argv[1] if len(sys.argv) > 1 else '127.0.0.1'
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 6666
WORKSTATION = sys.argv[3] if len(sys.argv) > 3 else 'A'   # A=Administrator
USER, PASSWORD, DB = 'MASTER', '1', 'IBIS'
CLIENT_ID = 100000 + random.randint(0, 899999)
QID = [0]

def execute(command, extra=None):
    QID[0] += 1
    lines = [command, WORKSTATION, command, str(CLIENT_ID), str(QID[0]), PASSWORD, USER, '', '', '']
    if extra:
        lines += extra
    body = ('\n'.join(lines) + '\n').encode('utf-8')
    packet = (str(len(body)) + '\n').encode('ascii') + body
    s = socket.create_connection((HOST, PORT), timeout=8)
    s.settimeout(8)
    s.sendall(packet)
    data = b''
    try:
        while True:
            ch = s.recv(65536)
            if not ch:
                break          # server closed -> response complete
            data += ch
    except socket.timeout:
        pass
    try: s.close()
    except Exception: pass
    return packet, data

def dump(label, req, resp, full=False):
    print('=' * 64)
    print(label)
    print('--- REQUEST (%d bytes) ---' % len(req))
    print(repr(req))
    print('--- RESPONSE (%d bytes) ---' % len(resp))
    txt = resp.decode('utf-8', 'replace')
    print(txt if full else txt[:600])
    if not full and len(txt) > 600:
        print('...(%d more chars)' % (len(txt) - 600))
    print('--- response hex (first 64) ---')
    print(resp[:64].hex(' '))

def main():
    outdir = os.path.dirname(os.path.abspath(__file__))
    sys.stdout = open(os.path.join(outdir, 'probe_results.txt'), 'w', encoding='utf-8')
    print('Server %s:%d, user=%s, workstation=%s, client_id=%d' % (HOST, PORT, USER, WORKSTATION, CLIENT_ID))
    # 0) best-effort cleanup of any stale MASTER registration (ignore result)
    try: execute('B', [USER])
    except Exception as e: print('pre-unreg note:', e)
    # 1) REGISTER (login) — expect INI profile + return code
    dump('1. REGISTER (A)', *execute('A', [USER, PASSWORD]), full=True)
    # 2) NOP / keepalive
    dump('2. NOP (N)', *execute('N'))
    # 3) GET MAX MFN (O) for a database
    dump('3. MAXMFN (O) %s' % DB, *execute('O', [DB]))
    # 4) SEARCH (K): db, expression, want-format(0), min, max, format
    dump('4. SEARCH (K) %s I=$' % DB, *execute('K', [DB, '"I=$"', '0', '1', '0', '']))
    # 5) UNREGISTER (B)
    dump('5. UNREGISTER (B)', *execute('B', [USER]))

if __name__ == '__main__':
    main()
