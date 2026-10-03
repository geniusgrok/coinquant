"""Verified read-only vault reuse before the original rolling tape loader."""
from datetime import datetime, timezone
import errno
import hashlib
import os
from pathlib import Path

from research.rolling_prints import RollingPrints

VAULT = Path('/workspace/scratch/alpha-beta-next/public-print-vault')


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


class VerifiedPrints(RollingPrints):
    def __init__(self, root, vault=VAULT):
        self.vault = Path(vault).resolve()
        root = Path(root).resolve()
        if root.is_relative_to(self.vault) or self.vault.is_relative_to(root):
            raise ValueError('rolling cache and immutable vault must be separate')
        binary_cache = root.parent/(root.name+'-cache')
        if binary_cache.is_symlink() or binary_cache.resolve().is_relative_to(self.vault):
            raise ValueError('binary cache must not alias the immutable vault')
        super().__init__(root)
        self.receipts = []

    @staticmethod
    def _link(source, destination):
        try:
            os.link(source, destination)
        except OSError as exc:
            if exc.errno != errno.EXDEV:
                raise
            with source.open('rb') as reader, destination.open('xb') as writer:
                while block := reader.read(1024*1024):
                    writer.write(block)

    def _load(self, day_ms):
        if self._day_ms == day_ms:
            return super()._load(day_ms)
        name = f'BTCUSDT-aggTrades-{datetime.fromtimestamp(day_ms/1000, timezone.utc):%Y-%m-%d}.zip'
        source, target = self.vault/name, self.root/name
        checksum_source = Path(str(source)+'.CHECKSUM')
        checksum_target = Path(str(target)+'.CHECKSUM')
        restored = False
        if target.is_symlink() or checksum_target.is_symlink() or (not target.exists() and checksum_target.exists()):
            raise ValueError('never overwrite an existing cache destination')
        if not target.exists() and source.exists():
            if target.is_symlink() or checksum_target.exists() or checksum_target.is_symlink():
                raise ValueError('never overwrite an existing cache destination')
            fields = checksum_source.read_text().split()
            if len(fields) != 2 or fields[1].lstrip('*') != name or digest(source) != fields[0]:
                raise ValueError('vault ZIP does not match official CHECKSUM')
            self._link(source, target)
            self._link(checksum_source, checksum_target)
            restored = True
        rows = super()._load(day_ms)
        if rows is not None:
            actual = self.loaded[name]
            if digest(target) != actual:
                raise ValueError('restore receipt differs from consumed tape')
            self.receipts.append({'name': name, 'sha256': actual,
                'checksum_sha256': digest(checksum_target),
                'source': str(source) if restored else 'original_rolling_loader',
                'method': 'verified_link_or_exclusive_copy' if restored else 'original_rolling_loader'})
        return rows
