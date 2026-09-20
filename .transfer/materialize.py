"""Export and verify recovery sources without changing files or pushing any ref.

The packet and later Git tree are separate inputs, not interchangeable versions.
No credentials, financial requests, network access, or repository writes.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import tarfile
import tempfile
import zipfile


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def oid(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def safe_path(name: str) -> str:
    path = PurePosixPath(name)
    require(bool(name) and not path.is_absolute(), "absolute or empty path")
    require(".." not in path.parts and ".git" not in path.parts, "unsafe path")
    require(path.as_posix() == name, "noncanonical path")
    return name


def export(root: Path, output: Path) -> dict:
    def git(*args: str) -> bytes:
        return subprocess.check_output(["git", "-C", str(root), *args])

    head = git("rev-parse", "HEAD").decode().strip()
    before = git("status", "--porcelain", "--untracked-files=all")
    manifest = json.loads((root / ".transfer/manifest.json").read_text())
    require(manifest["archive_format"] == "tar.xz", "unknown archive format")
    packet = bytearray()
    for index, part in enumerate(manifest["parts"]):
        require(part["index"] == index and part["offset"] == len(packet), "part ordering/offset")
        path = safe_path(part["path"])
        data = (root / ".transfer" / path).read_bytes()
        require(len(data) == part["length"] and sha256(data) == part["sha256"], "part length/hash")
        require(oid(data) == part["git_blob_oid"], "part Git blob ID")
        packet.extend(data)
    require(len(packet) == manifest["archive_length"], "archive length")
    require(sha256(packet) == manifest["archive_sha256"], "archive hash")
    expected = {safe_path(item["path"]): item for item in manifest["files"]}
    require(len(expected) == len(manifest["files"]), "duplicate manifest path")
    output.parent.mkdir(parents=True, exist_ok=True)
    inventory = []
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as target:
        with tarfile.open(fileobj=io.BytesIO(packet), mode="r:xz") as source:
            members = source.getmembers()
            require(len(members) == len(expected), "archive member count")
            require({m.name for m in members} == set(expected), "archive file set")
            for member in members:
                require(member.isfile() and not member.issym() and not member.islnk(), "non-regular archive member")
                item = expected[member.name]
                require(member.size == item["bytes"], "archive member size")
                with source.extractfile(member) as stream:
                    data = stream.read()
                require(sha256(data) == item["sha256"] and oid(data) == item["git_blob_oid"], "archive member identity")
                target.writestr("packet/" + member.name, data)
        for record in git("ls-tree", "-r", "-z", "HEAD").split(b"\0"):
            if not record:
                continue
            meta, raw_path = record.split(b"\t", 1)
            mode, kind, blob_id = meta.decode().split()
            path = safe_path(raw_path.decode())
            require(kind == "blob" and mode in ("100644", "100755"), "unsupported Git entry")
            data = git("cat-file", "blob", blob_id)
            require(oid(data) == blob_id, "Git tree blob mismatch")
            target.writestr("snapshot/" + path, data)
            inventory.append({"path": path, "bytes": len(data), "sha256": sha256(data), "git_blob_oid": blob_id})
        receipt = {"status": "VERIFIED_EXPORT_NOT_INTEGRATED", "source_commit": head,
                   "packet_sha256": manifest["archive_sha256"], "files": inventory,
                   "warning": "Reconcile packet and snapshot explicitly; never overwrite later code blindly."}
        target.writestr("receipt.json", json.dumps(receipt, indent=2) + "\n")
    require(git("status", "--porcelain", "--untracked-files=all") == before, "repository changed during export")
    return {"source_commit": head, "archive": str(output), "bytes": output.stat().st_size,
            "sha256": sha256(output.read_bytes()), "snapshot_files": len(inventory), "packet_files": len(expected)}


if __name__ == "__main__":
    output = Path(os.environ.get("RUNNER_TEMP", tempfile.gettempdir())) / "pancakequant-recovery" / "recovery.zip"
    print(json.dumps(export(Path.cwd(), output), sort_keys=True))
