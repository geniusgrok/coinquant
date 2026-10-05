"""One manual, bounded paired public capture with FX level2_batch; never reconnects.

The 10s warmup, 20s event window and 10s boundary tail are frozen before the
two connections. Missing fences/freshness remain negative; no shifted window,
accounts, daemon or trading adapter. Framing follows the original accepted
stdlib stream capture; each stream is capped at 4 MiB and each message 256 KiB.
"""
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import socket
import ssl
import struct
import time
from urllib.parse import unquote, urlsplit

from research.information_next import DOCS, compile_window

LIMIT = 4 * 1024 * 1024
FRAME_LIMIT = 256 * 1024
TASKS = [dict(venue='coinbase', url='wss://ws-feed.exchange.coinbase.com', subscribe=dict(
    type='subscribe', channels=[dict(name='matches', product_ids=['BTC-USD']),
        dict(name='heartbeat', product_ids=['BTC-USD']),
        dict(name='level2_batch', product_ids=['USDT-USD'])])),
    dict(venue='kraken', url='wss://ws.kraken.com/v2', subscribe=dict(method='subscribe',
        params=dict(channel='trade', symbol=['BTC/USD'], snapshot=False), req_id=1))]


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def remaining(deadline):
    value = deadline - time.monotonic()
    if value <= 0:
        raise TimeoutError('REGISTERED_DEADLINE_REACHED')
    return value


class Reader:
    def __init__(self, sock, deadline):
        self.sock, self.deadline, self.buf = sock, deadline, b''

    def exact(self, size):
        while len(self.buf) < size:
            self.sock.settimeout(remaining(self.deadline))
            chunk = self.sock.recv(min(65536, max(4096, size - len(self.buf))))
            if not chunk:
                raise EOFError('REMOTE_CONNECTION_ENDED')
            self.buf += chunk
        result, self.buf = self.buf[:size], self.buf[size:]
        return result

    def header(self):
        while b'\r\n\r\n' not in self.buf:
            if len(self.buf) > 65536:
                raise ValueError('HANDSHAKE_HEADER_TOO_LARGE')
            self.sock.settimeout(remaining(self.deadline))
            chunk = self.sock.recv(4096)
            if not chunk:
                raise EOFError('HANDSHAKE_CONNECTION_ENDED')
            self.buf += chunk
        result, self.buf = self.buf.split(b'\r\n\r\n', 1)
        return result + b'\r\n\r\n'


def send(sock, opcode, payload):
    mask = os.urandom(4)
    size = len(payload)
    header = bytes([0x80 | opcode])
    header += (bytes([0x80 | size]) if size < 126 else
               bytes([0xfe]) + struct.pack('!H', size) if size < 65536 else
               bytes([0xff]) + struct.pack('!Q', size))
    sock.sendall(header + mask + bytes(value ^ mask[i % 4] for i, value in enumerate(payload)))


def capture(task, directory, deadline):
    venue = task['venue']
    rec = dict(venue=venue, url=task['url'], subscribe=task['subscribe'], attempt_ns=time.time_ns(),
        status='ATTEMPTED', connection_attempts=1, reconnects=0, private_request=False,
        TLS_verified=False, failures=[], messages=0, raw_messages_file=venue + '-messages.ndjson')
    sock = None
    rawpath = directory / rec['raw_messages_file']
    try:
        proxy_raw = (os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
                     or os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy'))
        if not proxy_raw:
            raise ValueError('INHERITED_PROXY_MISSING_NO_DIRECT_FALLBACK')
        proxy, target = urlsplit(proxy_raw), urlsplit(task['url'])
        if proxy.scheme != 'http':
            raise ValueError('UNSUPPORTED_PROXY_NO_FALLBACK')
        handshake = min(deadline, time.monotonic() + 8)
        sock = socket.create_connection((proxy.hostname, proxy.port or 80), timeout=remaining(handshake))
        request = f'CONNECT {target.hostname}:443 HTTP/1.1\r\nHost: {target.hostname}:443\r\n'
        if proxy.username is not None:
            auth = unquote(proxy.username) + ':' + unquote(proxy.password or '')
            request += 'Proxy-Authorization: Basic ' + base64.b64encode(auth.encode()).decode() + '\r\n'
        sock.sendall((request + '\r\n').encode())
        reader = Reader(sock, handshake)
        response = reader.header()
        (directory / (venue + '-proxy-handshake.raw')).write_bytes(response)
        rec['proxy_http_status'] = int(response.split(b' ', 2)[1])
        if rec['proxy_http_status'] != 200 or reader.buf:
            raise ValueError('PROXY_CONNECT_NOT_QUALIFIED')
        sock.settimeout(remaining(handshake))
        sock = ssl.create_default_context().wrap_socket(sock, server_hostname=target.hostname)
        rec['TLS_verified'] = True
        key = base64.b64encode(os.urandom(16)).decode()
        request = (f'GET {target.path or "/"} HTTP/1.1\r\nHost: {target.hostname}\r\n'
            'Upgrade: websocket\r\nConnection: Upgrade\r\n'
            f'Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n'
            'User-Agent: BTCResearchClosedWindow/1.0\r\n\r\n')
        sock.sendall(request.encode())
        reader = Reader(sock, handshake)
        response = reader.header()
        (directory / (venue + '-websocket-handshake.raw')).write_bytes(response)
        rec['websocket_http_status'] = int(response.split(b' ', 2)[1])
        headers = {s.split(b':', 1)[0].lower(): s.split(b':', 1)[1].strip()
                   for s in response.split(b'\r\n')[1:] if b':' in s}
        accept = base64.b64encode(hashlib.sha1((key + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest())
        if rec['websocket_http_status'] != 101 or headers.get(b'sec-websocket-accept') != accept:
            raise ValueError('INVALID_WEBSOCKET_UPGRADE')
        reader.deadline = deadline
        rec.update(status='CONNECTED', connected_ns=time.time_ns())
        send(sock, 1, json.dumps(task['subscribe'], separators=(',', ':')).encode())
        chunks, opcode, written = [], None, 0
        with rawpath.open('xb') as stream:
            while True:
                first = reader.exact(2)
                fin, kind, size = bool(first[0] & 0x80), first[0] & 15, first[1] & 127
                if first[0] & 0x70 or first[1] & 0x80:
                    raise ValueError('UNNEGOTIATED_OR_MASKED_SERVER_FRAME')
                if size == 126:
                    size = struct.unpack('!H', reader.exact(2))[0]
                elif size == 127:
                    size = struct.unpack('!Q', reader.exact(8))[0]
                if size > FRAME_LIMIT:
                    raise ValueError('REGISTERED_FRAME_BYTES_LIMIT')
                payload = reader.exact(size)
                if kind == 9:
                    send(sock, 10, payload)
                    continue
                if kind == 10:
                    continue
                if kind == 8:
                    raise EOFError('REMOTE_CLOSE_BEFORE_REGISTERED_DEADLINE')
                if kind == 1 and opcode is None:
                    chunks, opcode = [payload], 1
                elif kind == 0 and opcode == 1:
                    chunks.append(payload)
                else:
                    raise ValueError('UNEXPECTED_TEXT_FRAME_SEQUENCE')
                if sum(map(len, chunks)) > FRAME_LIMIT:
                    raise ValueError('REGISTERED_MESSAGE_BYTES_LIMIT')
                if fin:
                    payload = b''.join(chunks)
                    item = dict(receipt_ns=time.time_ns(), opcode=1,
                        raw_sha256=hashlib.sha256(payload).hexdigest(), raw_text=payload.decode())
                    line = (json.dumps(item, separators=(',', ':')) + '\n').encode()
                    if written + len(line) > LIMIT:
                        raise ValueError('REGISTERED_STREAM_BYTES_LIMIT')
                    stream.write(line)
                    written += len(line)
                    rec['messages'] += 1
                    chunks, opcode = [], None
    except TimeoutError as exc:
        if rec['status'] == 'CONNECTED' and time.monotonic() >= deadline:
            rec['status'] = 'FIXED_WINDOW_STOP'
        else:
            rec['status'] = 'CAPTURE_FAILED'
            rec['failures'].append(dict(error=type(exc).__name__, reason=str(exc)[:160]))
    except Exception as exc:
        rec['status'] = 'CAPTURE_FAILED'
        rec['failures'].append(dict(error=type(exc).__name__, reason=str(exc)[:160]))
    finally:
        if sock is not None:
            sock.close()
        if not rawpath.exists():
            rawpath.write_bytes(b'')
        raw = rawpath.read_bytes()
        rec.update(ended_ns=time.time_ns(), raw_bytes=len(raw), raw_messages_sha256=hashlib.sha256(raw).hexdigest())
        save(directory / (venue + '-connection-receipt.json'), rec)
    return rec


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--semantics-root', type=Path, required=True)
    parser.add_argument('--purpose', required=True)
    args = parser.parse_args()
    semantics = {}
    for venue, name in (('coinbase', 'coinbase-ws-channels.raw'), ('kraken', 'kraken-ws-v2-trade-redirect-target.raw')):
        path = args.semantics_root / name
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != DOCS[venue]:
            raise ValueError('original accepted semantics required before capture')
        semantics[venue] = dict(path=str(path), sha256=digest)
    args.out.mkdir(exist_ok=False)
    began = time.monotonic()
    registered = time.time_ns()
    plan = dict(format='btc-closed-information-window-v1', registered_ns=registered,
        start_ns=registered + 10_000_000_000, end_ns=registered + 30_000_000_000,
        decision_ns=registered + 40_000_000_000, semantics=semantics,
        connection_attempts=2, reconnects=0, orders=0, private_requests=0,
        budget=dict(total_seconds=40, warmup_seconds=10, window_seconds=20, tail_seconds=10,
                    per_stream_bytes=LIMIT, total_raw_bytes=2 * LIMIT, message_bytes=FRAME_LIMIT),
        source_path=str(Path(__file__).resolve()), source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        qualifier_source_sha256=hashlib.sha256(Path(__file__).with_name('information_next.py').read_bytes()).hexdigest(),
        frozen_before_connections=True, no_retry_or_shift=True, tasks=TASKS, purpose=args.purpose)
    save(args.out / 'registered-plan.json', plan)
    with ThreadPoolExecutor(max_workers=2) as pool:
        receipts = list(pool.map(lambda task: capture(task, args.out, began + 40), TASKS))
    plan['streams'] = [dict(venue=rec['venue'], receipt_path=str(args.out / (rec['venue'] + '-connection-receipt.json')),
        receipt_sha256=hashlib.sha256((args.out / (rec['venue'] + '-connection-receipt.json')).read_bytes()).hexdigest())
        for rec in receipts]
    save(args.out / 'bound-window-plan.json', plan)
    try:
        result = compile_window(plan)
    except (ValueError, KeyError, TypeError, ArithmeticError) as exc:
        result = dict(status='BLOCK_CAPTURE', reason=str(exc), orders=0, account_entrants=0)
    result.update(elapsed_seconds=time.monotonic() - began, attempts=2, new_capture=1, reconnects=0,
                  raw_bytes=sum(rec['raw_bytes'] for rec in receipts), mature_outcomes=0)
    save(args.out / 'result.json', result)
    print(json.dumps({key: result.get(key) for key in ('status', 'blockers', 'reason', 'raw_bytes', 'elapsed_seconds')}))


if __name__ == '__main__':
    main()
