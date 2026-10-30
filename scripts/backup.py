"""Back up and check a backup of a JARVIS installation (Beta plan BR-8, acceptance B-09).

    py -3.14 scripts/backup.py create  <destination> [--config PATH]
    py -3.14 scripts/backup.py verify  <destination>

`create` copies the data root (the database through SQLite's own backup API, so a copy
taken while JARVIS runs is consistent; HEAD; memory, briefs, results, reports) and the
governance zone into a NEW, empty folder outside both, with a manifest of SHA-256
hashes. It never changes the installation.

`verify` restores the backup into a scratch folder, checks every hash in the manifest,
runs the audit-chain verification and compares HEAD. It never touches the installation
and deletes its scratch copy.

This is an operator tool in scripts/, not part of the control plane: it is not imported
by jarvis/, runs nothing, and uses only the standard library. It creates no process and
makes no connection. Restoring onto the live install is a manual, deliberate step: see
docs/beta/BETA_OPERATIONS.md.
"""

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from jarvis import config as config_mod  # noqa: E402
from jarvis.store import Store, StoreError  # noqa: E402

MANIFEST = "MANIFEST.json"
DATA_DIRS = ("memory", "briefs", "results", "reports")
FORMAT = 1


class BackupError(RuntimeError):
    pass


def _sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def _inside(path: str, root: str) -> bool:
    path, root = os.path.normcase(os.path.realpath(path)), os.path.normcase(os.path.realpath(root))
    try:
        return os.path.commonpath([path, root]) == root
    except ValueError:
        return False


def _copy_tree(src: str, dst: str) -> None:
    for folder, _dirs, files in os.walk(src):
        target = os.path.join(dst, os.path.relpath(folder, src))
        os.makedirs(target, exist_ok=True)
        for name in files:
            shutil.copy2(os.path.join(folder, name), os.path.join(target, name))


def create(cfg, destination: str) -> dict:
    dest = os.path.abspath(destination)
    for root in (cfg.data_root, cfg.governance_zone):
        if _inside(dest, root) or _inside(root, dest):
            raise BackupError("DESTINATION_OVERLAPS_THE_INSTALL")
    if os.path.exists(dest) and os.listdir(dest):
        raise BackupError("DESTINATION_NOT_EMPTY")
    if not Store.exists(cfg.data_root):
        raise BackupError("STORE_MISSING")
    os.makedirs(os.path.join(dest, "data"), exist_ok=True)

    source = sqlite3.connect("file:%s?mode=ro" % Store.db_path(cfg.data_root).replace("\\", "/"), uri=True)
    try:
        target = sqlite3.connect(os.path.join(dest, "data", os.path.basename(Store.db_path(cfg.data_root))))
        try:
            source.backup(target)
        finally:
            target.close()
    finally:
        source.close()
    head = os.path.join(cfg.data_root, "HEAD")
    if os.path.isfile(head):
        shutil.copy2(head, os.path.join(dest, "data", "HEAD"))
    for name in DATA_DIRS:
        folder = os.path.join(cfg.data_root, name)
        if os.path.isdir(folder):
            _copy_tree(folder, os.path.join(dest, "data", name))
    _copy_tree(cfg.governance_zone, os.path.join(dest, "governance"))

    files = {}
    for folder, _dirs, names in os.walk(dest):
        for name in names:
            path = os.path.join(folder, name)
            rel = os.path.relpath(path, dest).replace("\\", "/")
            if rel != MANIFEST:
                files[rel] = _sha256(path)
    manifest = {"format": FORMAT, "created": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "config_sha256": cfg.sha256, "files": dict(sorted(files.items()))}
    with open(os.path.join(dest, MANIFEST), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True)
        fh.write("\n")
    return manifest


def verify(destination: str) -> dict:
    """Restore into a scratch folder and prove the backup is whole and the chain verifies."""
    dest = os.path.abspath(destination)
    try:
        with open(os.path.join(dest, MANIFEST), encoding="utf-8") as fh:
            manifest = json.load(fh)
    except (OSError, ValueError):
        raise BackupError("MANIFEST_MISSING_OR_INVALID") from None
    if manifest.get("format") != FORMAT:
        raise BackupError("MANIFEST_FORMAT_UNKNOWN")
    for rel, expected in manifest["files"].items():
        path = os.path.join(dest, *rel.split("/"))
        if not os.path.isfile(path):
            raise BackupError("FILE_MISSING %s" % rel)
        if _sha256(path) != expected:
            raise BackupError("FILE_CHANGED %s" % rel)
    present = set()
    for folder, _dirs, names in os.walk(dest):
        for name in names:
            rel = os.path.relpath(os.path.join(folder, name), dest).replace("\\", "/")
            if rel != MANIFEST:
                present.add(rel)
    extra = sorted(present - set(manifest["files"]))
    if extra:
        raise BackupError("FILE_NOT_IN_MANIFEST %s" % extra[0])

    scratch = tempfile.mkdtemp(prefix="jarvis-restore-check-")
    try:
        restored = os.path.join(scratch, "data")
        shutil.copytree(os.path.join(dest, "data"), restored)
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        try:
            store = Store.open(restored, now, "backup-verify")
        except StoreError as exc:
            raise BackupError("STORE_%s" % exc.code) from None
        try:
            result = store.verify()
            problems = list(result.problems) + store.head_check(result)
            if problems or store.halted:
                raise BackupError("AUDIT_CHAIN %s" % "; ".join(problems or store.findings))
            return {"files": len(manifest["files"]), "tail_seq": result.tail_seq,
                    "tail_hash": result.tail_hash, "created": manifest["created"]}
        finally:
            store.close()
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="backup.py", description=__doc__.split("\n")[0])
    parser.add_argument("--config", default=config_mod.DEFAULT_CONFIG_PATH)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("create").add_argument("destination")
    sub.add_parser("verify").add_argument("destination")
    args = parser.parse_args(argv)
    try:
        if args.command == "create":
            manifest = create(config_mod.load(args.config), args.destination)
            print("backup created: %s" % os.path.abspath(args.destination))
            print("files: %d" % len(manifest["files"]))
            print("next: py -3.14 scripts/backup.py verify %s" % args.destination)
        else:
            info = verify(args.destination)
            print("backup verify: OK")
            print("files: %d  audit tail seq: %s  created: %s" % (info["files"], info["tail_seq"], info["created"]))
        return 0
    except (BackupError, config_mod.ConfigError) as exc:
        print("backup %s: FAILED: %s" % (args.command, getattr(exc, "code", None) or exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())
