"""Command-line interface (ADR-0002 D1 row 9). Record voice only.

This milestone implements `status` and `audit verify`. `task`, `report` and
`cancel` follow with the policy loader.

Exit codes: 0 ok; 2 usage; 3 configuration error; 4 store missing;
5 audit verification failed or store halted; 6 store busy; 1 unexpected error.
Every unexpected error fails closed.
"""

import argparse
import os
import sys
from datetime import datetime, timezone

from . import config as config_mod
from .store import Store, StoreError

EXIT_OK, EXIT_UNEXPECTED, EXIT_USAGE = 0, 1, 2
EXIT_CONFIG, EXIT_STORE_MISSING, EXIT_AUDIT, EXIT_BUSY = 3, 4, 5, 6


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def os_actor() -> str:
    """The OS user. It does not establish a human (ADR-0005 D8)."""
    try:
        return os.getlogin()
    except OSError:
        return "UNKNOWN"


def _print(out, *lines):
    for line in lines:
        out.write(line + "\n")


def cmd_status(cfg, out) -> int:
    _print(out, "JARVIS status", "config_sha256: %s" % cfg.sha256)
    if not Store.exists(cfg.data_root):
        _print(out, "store: not initialized")
        return EXIT_OK
    store = Store.open(cfg.data_root, utc_now(), os_actor(), cfg.busy_timeout_ms)
    try:
        result = store.verify()
        _print(out, "store: initialized",
               "audit_tail_seq: %s" % result.tail_seq,
               "halted: %s" % ("yes" if store.halted else "no"),
               "findings: %s" % (", ".join(store.findings) or "none"))
        counts = store.count_by_state()
        _print(out, "tasks: %s" % (", ".join("%s=%d" % kv for kv in sorted(counts.items())) or "none"))
        return EXIT_AUDIT if store.halted else EXIT_OK
    finally:
        store.close()


def cmd_audit_verify(cfg, out) -> int:
    if not Store.exists(cfg.data_root):
        _print(out, "audit verify: store missing")
        return EXIT_STORE_MISSING
    store = Store.open(cfg.data_root, utc_now(), os_actor(), cfg.busy_timeout_ms)
    try:
        result = store.verify()
        problems = list(result.problems) + store.head_check(result)
        if problems or store.halted:
            _print(out, "audit verify: FAILED", *("problem: %s" % p for p in problems or store.findings))
            return EXIT_AUDIT
        _print(out, "audit verify: OK", "tail_seq: %d" % result.tail_seq,
               "tail_hash: %s" % result.tail_hash)
        return EXIT_OK
    finally:
        store.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="jarvis", description="JARVIS Phase 1 control plane")
    parser.add_argument("--config", default=config_mod.DEFAULT_CONFIG_PATH,
                        help="configuration file in the governance zone")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="show control-plane status")
    audit = sub.add_parser("audit", help="audit chain operations")
    audit_sub = audit.add_subparsers(dest="audit_command", required=True)
    audit_sub.add_parser("verify", help="verify the audit chain from genesis")
    return parser


def main(argv=None, out=None) -> int:
    out = out or sys.stdout
    try:
        args = build_parser().parse_args(argv)
    except SystemExit as exc:
        return EXIT_USAGE if exc.code else EXIT_OK
    try:
        cfg = config_mod.load(args.config)
    except config_mod.ConfigError as exc:
        _print(out, "configuration error: %s" % exc.code)
        return EXIT_CONFIG
    try:
        if args.command == "status":
            return cmd_status(cfg, out)
        if args.command == "audit" and args.audit_command == "verify":
            return cmd_audit_verify(cfg, out)
        return EXIT_USAGE
    except StoreError as exc:
        _print(out, "store error: %s" % exc.code)
        return EXIT_BUSY if exc.code == "STORE_BUSY" else EXIT_AUDIT
    except Exception as exc:  # fail closed
        _print(out, "unexpected error: %s" % type(exc).__name__)
        return EXIT_UNEXPECTED
