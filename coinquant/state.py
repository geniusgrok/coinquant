"""Local single-writer lock and synchronous durable exchange intents.

The database is a recovery aid, never an authority for balances or positions.
Use one persistent state directory per account on one machine. Concurrent agents
on different machines require an external shared lease and are not supported.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sqlite3
from time import time

from .types import Blocked, Unknown, serial, number


def client_id(account: str, candle: int, operation: str) -> str:
    # Independent of local state and parameters: lost state cannot change an ID.
    identity = f'BTCUSD|{account}|{candle}|{operation}'.encode()
    return 'cq-' + hashlib.sha256(identity).hexdigest()[:30]


class State:
    def __init__(self, directory: str | Path, identity: str):
        self.directory = Path(directory).expanduser().resolve()
        self.identity = identity
        self.lock = None
        self.db = None

    def __enter__(self):
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.lock = open(self.directory / 'execution.lock', 'a+b')
        try:
            if os.name == 'nt':
                import msvcrt
                self.lock.seek(0)
                if self.lock.read(1) == b'':
                    self.lock.write(b'0'); self.lock.flush()
                self.lock.seek(0)
                msvcrt.locking(self.lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.db = sqlite3.connect(self.directory / 'intents.sqlite', timeout=0)
            self.db.execute('PRAGMA synchronous=FULL')
            self.db.execute('CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
            self.db.execute('CREATE TABLE IF NOT EXISTS intents (id TEXT PRIMARY KEY, kind TEXT NOT NULL, payload TEXT NOT NULL, status TEXT NOT NULL, result TEXT NOT NULL, updated REAL NOT NULL)')
            saved = self.get('identity')
            if saved is not None and saved != self.identity:
                raise Blocked('state directory belongs to another account or environment')
            self.set('identity', self.identity)
            return self
        except (OSError, sqlite3.Error) as exc:
            self.__exit__(None, None, None)
            raise Blocked('state unavailable or another run holds the execution lock') from exc
        except Exception:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, *args):
        if self.db is not None:
            self.db.close(); self.db = None
        if self.lock is not None:
            # Closing releases the OS lock. Never cancel exchange orders here.
            self.lock.close(); self.lock = None

    def get(self, key: str):
        row = self.db.execute('SELECT value FROM meta WHERE key=?', (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def set(self, key: str, value) -> None:
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO meta VALUES (?,?)',
                            (key, json.dumps(serial(value), sort_keys=True)))

    def prepare(self, identity: str, kind: str, payload: dict, *, campaign=None, flat_snapshot=None) -> None:
        encoded = json.dumps(serial(payload), sort_keys=True, separators=(',', ':'))
        row = self.db.execute('SELECT payload FROM intents WHERE id=?', (identity,)).fetchone()
        if row:
            raise Unknown('intent already exists; reconcile it instead of resending')
        links=None
        if campaign is not None:
            if (type(campaign) is not int or campaign<=0 or kind!='binance_order'
                    or payload.get('symbol')!='BTCUSDT' or payload.get('positionSide')!='BOTH'
                    or payload.get('side') not in ('BUY','SELL') or payload.get('reduceOnly')=='true'
                    or not flat_snapshot or number(flat_snapshot.get('quantity_btc'))!=0
                    or flat_snapshot.get('possible_entry_remainders')!=0
                    or self.pending()
                    or self.identity!=f"binance:BTCUSDT:live:{flat_snapshot.get('account_uid')}"):
                raise Blocked('entry campaign requires a reconciled flat owned account')
            links=self.get('entry_campaigns') or {}
            links[identity]=dict(campaign=campaign,prepared_at=int(time()*1000))
        with self.db:
            self.db.execute('INSERT INTO intents VALUES (?,?,?,?,?,?)',
                            (identity, kind, encoded, 'unknown', '{}', time()))
            if links is not None:
                self.db.execute('INSERT OR REPLACE INTO meta VALUES (?,?)',('entry_campaigns',json.dumps(links,sort_keys=True)))
        # A crash immediately after this commit must be treated as possibly sent.

    def finish(self, identity: str, status: str, result: dict) -> None:
        if status not in ('unknown', 'partial', 'confirmed', 'rejected'):
            raise ValueError('invalid intent status')
        prior=self.db.execute('SELECT result FROM intents WHERE id=?',(identity,)).fetchone()
        if prior:
            old=json.loads(prior[0]).get('executed_quantity')
            if old is not None and (result.get('executed_quantity') is None
                    or number(result['executed_quantity'])<number(old)):
                raise Unknown('native cumulative fill cannot regress or disappear')
        with self.db:
            cursor = self.db.execute('UPDATE intents SET status=?,result=?,updated=? WHERE id=?',
                                    (status, json.dumps(serial(result), sort_keys=True), time(), identity))
            if cursor.rowcount != 1:
                raise Blocked('cannot finish an unrecorded intent')

    def pending(self) -> list[dict]:
        return [dict(id=a, kind=b, payload=json.loads(c), status=d)
                for a, b, c, d in self.db.execute(
                    "SELECT id,kind,payload,status FROM intents WHERE status IN ('unknown','partial') ORDER BY updated")]

    def report(self, value: dict) -> None:
        # Reports deliberately exclude raw API-key metadata and signed requests.
        output = self.directory / 'latest.json'
        temporary = output.with_suffix('.tmp')
        with open(temporary, 'w', encoding='utf-8') as stream:
            json.dump(serial(value), stream, indent=2, allow_nan=False)
            stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, output)
        if os.name != 'nt':
            fd = os.open(self.directory, os.O_RDONLY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
