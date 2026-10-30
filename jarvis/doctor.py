"""Health check: is this installation ready to use? (Beta plan BR-7).

Runs the checks `status` and `audit verify` already rely on, plus the governance files,
the registry and each project's contract. It writes nothing of its own: the store is
opened and verified exactly as `audit verify` does. Output carries closed reason codes
and counts, never file contents. PASS and WARN do not fail the command; FAIL does.
"""

import os
import sys
from dataclasses import dataclass
from typing import List

from . import briefs, canonicalizer, contracts, notes, registry, results, revocations
from . import policy as policy_mod
from .model import EffectiveContract, PolicyFailure, RevocationFailure
from .store import Store, StoreError
from .tasks import REPO_ROOT

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"
MIN_PYTHON = (3, 11)  # ADR-0006 section 2 item 2 (tomllib)


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str


def _python() -> Check:
    version = "%d.%d.%d" % sys.version_info[:3]
    ok = sys.version_info[:2] >= MIN_PYTHON
    return Check("python", PASS if ok else FAIL, version if ok else "%s, needs 3.11 or later" % version)


def _directory(name: str, path: str) -> Check:
    return Check(name, PASS if os.path.isdir(path) else FAIL,
                 "present" if os.path.isdir(path) else "missing")


def _store(cfg, policy_hashes_out: dict, now_utc: str, actor: str) -> List[Check]:
    if not Store.exists(cfg.data_root):
        return [Check("store", FAIL, "not initialized (run: jarvis init)")]
    try:
        store = Store.open(cfg.data_root, now_utc, actor, cfg.busy_timeout_ms)
    except StoreError as exc:
        return [Check("store", FAIL, exc.code)]
    try:
        result = store.verify()
        problems = list(result.problems) + store.head_check(result)
        if problems or store.halted:
            return [Check("audit chain", FAIL, "; ".join(problems or store.findings))]
        policy_hashes_out.update(store.known_policy_hashes())
        counts = store.count_by_state()
        tasks = ", ".join("%s=%d" % kv for kv in sorted(counts.items())) or "none"
        found = notes.audit_files(store, cfg.data_root)
        note_check = (Check("notes", FAIL, "; ".join(found)) if found
                      else Check("notes", PASS, "%d recorded, all match the chain" % len(notes.list_notes(store))))
        found = briefs.audit_files(store, cfg.data_root)
        brief_check = (Check("briefs", FAIL, "; ".join(found)) if found
                       else Check("briefs", PASS, "all match the chain"))
        found = results.audit_files(store, cfg.data_root)
        result_check = (Check("results", FAIL, "; ".join(found)) if found
                        else Check("results", PASS, "%d recorded, all match the chain" % len(results.list_results(store))))
        return [Check("store", PASS, "initialized"),
                Check("audit chain", PASS, "verified, tail seq %d" % result.tail_seq),
                Check("tasks", PASS, tasks), note_check, brief_check, result_check]
    finally:
        store.close()


def _governance(cfg, secrets) -> List[Check]:
    checks = []
    revoked = revocations.load(revocations.path_in(cfg.governance_zone))
    if isinstance(revoked, RevocationFailure):
        checks.append(Check("revocations", FAIL, revoked.reason))
    else:
        checks.append(Check("revocations", PASS, "loaded"))

    registered = registry.load(registry.path_in(cfg.governance_zone))
    if isinstance(registered, registry.RegistryFailure):
        status = WARN if registered.reason == "REGISTRY_MISSING" else FAIL
        detail = "%s (no project can be used until RK writes it)" % registered.reason \
            if status == WARN else registered.reason
        checks.append(Check("registry", status, detail))
        return checks
    checks.append(Check("registry", PASS, "%d project(s)" % len(registered.projects)))

    base = canonicalizer.build_roots(cfg.governance_zone, cfg.data_root, REPO_ROOT,
                                     cfg.user_home, secrets)
    usable, rejected = registry.resolve_roots(registered, base)
    for project in registered.projects:
        name = "project %s" % project.id
        if project.id in rejected:
            checks.append(Check(name, FAIL, "root rejected: %s" % rejected[project.id]))
        elif project.id not in usable:
            checks.append(Check(name, WARN, "no root registered"))
        else:
            contract = contracts.load(cfg.governance_zone, project.id, usable[project.id])
            if isinstance(contract, EffectiveContract):
                checks.append(Check(name, PASS, "root and contract load"))
            else:
                status = WARN if contract.reason == "CONTRACT_MISSING" else FAIL
                checks.append(Check(name, status, "contract: %s" % contract.reason))
    return checks


def run(cfg, policy_path: str, now_utc: str, actor: str) -> List[Check]:
    checks = [_python(), Check("config", PASS, "sha256 %s" % cfg.sha256[:12]),
              _directory("governance zone", cfg.governance_zone),
              _directory("data root", cfg.data_root)]
    known: dict = {}
    checks.extend(_store(cfg, known, now_utc, actor))
    loaded = policy_mod.load(policy_path, known)
    if isinstance(loaded, PolicyFailure):
        checks.append(Check("policy", FAIL, loaded.reason))
        secrets = ()
    else:
        checks.append(Check("policy", PASS, "version %d, sha256 %s"
                            % (loaded.snapshot.policy_version, loaded.snapshot.sha256[:12])))
        secrets = loaded.secret_locations
    checks.extend(_governance(cfg, secrets))
    return checks
