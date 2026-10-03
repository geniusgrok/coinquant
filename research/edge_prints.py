"""Verified read-only vault reuse before the original rolling tape loader."""
from datetime import datetime, timezone
import errno
import hashlib
import json
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
        self.binary_cache = binary_cache
        self.owner = binary_cache/'.edge-print-owner'
        # Every invocation gets a fresh derived directory. Existing bytes have no
        # trusted derivation in this process, even if accompanied by a manifest.
        binary_cache.mkdir(parents=True, exist_ok=False)
        with self.owner.open('x') as stream:
            json.dump({'format': 1, 'root': str(root), 'vault': str(self.vault)}, stream)
        self.binaries = {}
        super().__init__(root)
        self.receipts = []

    def _validate_binaries(self):
        if not isinstance(self.binaries, dict):
            raise ValueError('invalid derived tape provenance')
        if {p.name for p in self.binary_cache.iterdir()} != {self.owner.name, *self.binaries}:
            raise ValueError('unknown derived tape files; leave existing files untouched')
        for name, record in self.binaries.items():
            path = self.binary_cache/name
            if (not isinstance(record, dict) or set(record) != {'zip_sha256', 'binary_sha256'} or
                    not name.endswith('.'+record['zip_sha256']+'.bin') or
                    path.is_symlink() or not path.is_file() or digest(path) != record['binary_sha256']):
                raise ValueError('derived tape integrity/provenance mismatch')

    def _record_binary(self, name, zip_sha256):
        path = self.binary_cache/(name+'.'+zip_sha256+'.bin')
        if path.is_symlink() or not path.is_file():
            raise ValueError('derived tape was not generated in owned cache')
        self.binaries[path.name] = {'zip_sha256': zip_sha256, 'binary_sha256': digest(path)}
        self._validate_binaries()
        return self.binaries[path.name]['binary_sha256']

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
        self._validate_binaries()
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
        # Missing public days can also evict an older day in the original loader.
        self.binaries = {name: row for name, row in self.binaries.items()
                         if (self.binary_cache/name).exists()}
        if rows is not None:
            actual = self.loaded[name]
            if digest(target) != actual:
                raise ValueError('restore receipt differs from consumed tape')
            binary_sha256 = self._record_binary(name, actual)
            self.receipts.append({'name': name, 'sha256': actual, 'derived_binary_sha256': binary_sha256,
                'checksum_sha256': digest(checksum_target),
                'source': str(source) if restored else 'original_rolling_loader',
                'method': 'verified_link_or_exclusive_copy' if restored else 'original_rolling_loader'})
        else:
            self._validate_binaries()
        return rows
