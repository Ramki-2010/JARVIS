"""Single SQLite store for task state and the audit chain (ADR-0005, ADR-0006 4).

- One database in the data root. A state change and its audit record are written
  in one BEGIN IMMEDIATE transaction, so a crash leaves both or neither (D1, D12).
- The chain tail is read inside the same transaction that appends, so two
  writers cannot fork the chain (D2). A writer that cannot get the lock within
  the busy timeout fails closed.
- Records are canonical JSON bytes (D4). record_hash = SHA-256(record bytes);
  each record carries seq and prev_hash inside its bytes (D5).
- HEAD holds only the sequence number and hash of the latest record (D6).
- The audit table receives INSERTs only. That is a design rule, not an
  enforcement: the store is tamper-evident, not tamper-proof (D10).
"""

import os
import sqlite3
from dataclasses import dataclass, field
from typing import List, Optional

from . import EVALUATOR_VERSION
from . import canonical_json as cj
from . import states
from .model import SUPPORTED_CONTRACT_SCHEMAS, SUPPORTED_POLICY_SCHEMAS, TIMESTAMP_RE
from .reasons import Level

STORE_SCHEMA_VERSION = 1
DB_NAME = "jarvis.db"
HEAD_NAME = "HEAD"
GENESIS_PREV = "0" * 64

# Master Context section 18 minimum fields, present in every record (D5).
AUDIT_FIELDS = (
    "task_id", "timestamp", "project", "objective", "risk_level", "tools_used",
    "files_read", "files_modified", "commands_run", "research_sources", "models_used",
    "tests_run", "verification_results", "retries", "errors", "final_status",
    "approval_events",
)
_LIST_FIELDS = frozenset({"tools_used", "files_read", "files_modified", "commands_run",
                          "research_sources", "models_used", "tests_run",
                          "verification_results", "errors", "approval_events"})

_SCHEMA = (
    "CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL) STRICT",
    "CREATE TABLE audit_log (seq INTEGER PRIMARY KEY, record BLOB NOT NULL, "
    "record_hash TEXT NOT NULL) STRICT",
    "CREATE TABLE tasks (task_id TEXT PRIMARY KEY, project TEXT NOT NULL, "
    "objective TEXT NOT NULL, state TEXT NOT NULL, risk_level TEXT NOT NULL, "
    "policy_version INTEGER, policy_sha256 TEXT, contract_sha256 TEXT, "
    "verification TEXT NOT NULL, verification_provenance TEXT NOT NULL, "
    "created_utc TEXT NOT NULL, updated_utc TEXT NOT NULL, "
    "last_seq INTEGER NOT NULL REFERENCES audit_log(seq)) STRICT",
)


class StoreError(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class Evaluation:
    """Summary of a fresh evaluation, required to enter RUNNING, BLOCKED or
    DEFERRED from PENDING, DEFERRED or BLOCKED (ADR-0002 D2, ADR-0003 D11)."""

    outcome: str
    risk_level: Level
    policy_version: int
    policy_sha256: Optional[str]
    contract_sha256: Optional[str]
    capabilities: tuple
    # One dict per requested capability (capability, target, risk_level, verdict, reason).
    # Recorded in the audit detail so a decision can be reconstructed (ADR-0005).
    decisions: tuple = ()


@dataclass
class VerifyResult:
    ok: bool
    problems: List[str] = field(default_factory=list)
    tail_seq: Optional[int] = None
    tail_hash: Optional[str] = None


def _empty_fields() -> dict:
    out = {}
    for name in AUDIT_FIELDS:
        out[name] = [] if name in _LIST_FIELDS else (0 if name == "retries" else "")
    return out


def _check_ts(value: str) -> None:
    if not (isinstance(value, str) and TIMESTAMP_RE.match(value)):
        raise StoreError("TIMESTAMP_INVALID")


class Store:
    _HALTING = frozenset({"AUDIT_TRUNCATION_SUSPECTED", "HEAD_MISMATCH", "HEAD_INVALID"})

    def __init__(self, conn: sqlite3.Connection, data_root: str):
        self._conn = conn
        self.data_root = data_root
        self.halted = False
        self.findings: List[str] = []

    # ------------------------------------------------------------------ open
    @staticmethod
    def db_path(data_root: str) -> str:
        return os.path.join(data_root, DB_NAME)

    @classmethod
    def exists(cls, data_root: str) -> bool:
        return os.path.isfile(cls.db_path(data_root))

    @classmethod
    def _connect(cls, data_root: str, busy_timeout_ms: int) -> sqlite3.Connection:
        conn = sqlite3.connect(cls.db_path(data_root), isolation_level=None,
                               timeout=busy_timeout_ms / 1000.0)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA synchronous = FULL")
        conn.execute("PRAGMA busy_timeout = %d" % int(busy_timeout_ms))
        return conn

    @classmethod
    def create(cls, data_root: str, now_utc: str, actor: str, policies: tuple,
               busy_timeout_ms: int = 5000) -> "Store":
        """Create the database and the genesis record. policies is a tuple of
        (policy_version, policy_sha256) in force."""
        _check_ts(now_utc)
        if cls.exists(data_root):
            raise StoreError("STORE_EXISTS")
        conn = cls._connect(data_root, busy_timeout_ms)
        store = cls(conn, data_root)
        try:
            conn.execute("BEGIN IMMEDIATE")
            for stmt in _SCHEMA:
                conn.execute(stmt)
            conn.execute("INSERT INTO meta VALUES ('store_schema_version', ?)",
                         (str(STORE_SCHEMA_VERSION),))
            record = _empty_fields()
            record.update({
                "seq": 0, "prev_hash": GENESIS_PREV, "event": "GENESIS", "timestamp": now_utc,
                "actor": actor,
                "policies": [{"policy_version": v, "policy_sha256": h} for v, h in policies],
                "evaluator_version": EVALUATOR_VERSION,
                "schema_versions": {"store": STORE_SCHEMA_VERSION,
                                    "policy": sorted(SUPPORTED_POLICY_SCHEMAS),
                                    "contract": sorted(SUPPORTED_CONTRACT_SCHEMAS)},
            })
            record["provenance"] = store._provenance(record)
            data = cj.dumps(record)
            digest = cj.sha256_hex(data)
            conn.execute("INSERT INTO audit_log VALUES (0, ?, ?)", (data, digest))
            conn.execute("COMMIT")
        except Exception:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            conn.close()
            raise
        store._write_head(0, digest)
        return store

    @classmethod
    def open(cls, data_root: str, now_utc: str, actor: str,
             busy_timeout_ms: int = 5000) -> "Store":
        """Open an existing store and run start-up checks (D12)."""
        _check_ts(now_utc)
        if not cls.exists(data_root):
            raise StoreError("STORE_MISSING")
        conn = cls._connect(data_root, busy_timeout_ms)
        store = cls(conn, data_root)
        row = conn.execute("PRAGMA quick_check").fetchone()
        if row is None or row[0] != "ok":
            conn.close()
            raise StoreError("STORE_INTEGRITY_FAILED")
        store._startup(now_utc, actor)
        return store

    def close(self) -> None:
        self._conn.close()

    # ------------------------------------------------------------ recording
    @staticmethod
    def _provenance(record: dict) -> dict:
        # Everything recorded here is computed or observed by the control
        # plane, except the actor, which is the OS user and does not establish a
        # human (ADR-0005 D8). Task objective text is supplied by RK: MEDIATED.
        prov = {k: "OBSERVED" for k in record if k != "provenance"}
        if "objective" in prov:
            prov["objective"] = "MEDIATED"
        return prov

    def _tail(self):
        row = self._conn.execute(
            "SELECT seq, record_hash FROM audit_log ORDER BY seq DESC LIMIT 1").fetchone()
        if row is None:
            raise StoreError("CHAIN_EMPTY")
        return row

    def _append(self, event: str, now_utc: str, actor: str, fields: dict) -> int:
        """Append one record. Must run inside an open write transaction."""
        seq, prev = self._tail()
        record = _empty_fields()
        record.update(fields)
        record.update({"seq": seq + 1, "prev_hash": prev, "event": event,
                       "timestamp": now_utc, "actor": actor})
        record["provenance"] = self._provenance(record)
        data = cj.dumps(record)
        digest = cj.sha256_hex(data)
        self._conn.execute("INSERT INTO audit_log VALUES (?, ?, ?)", (seq + 1, data, digest))
        self._pending_head = (seq + 1, digest)
        return seq + 1

    def _write(self, fn, update_head: bool = True):
        """Run fn inside BEGIN IMMEDIATE ... COMMIT, then update HEAD unless told
        to leave it as found."""
        self._pending_head = None
        try:
            self._conn.execute("BEGIN IMMEDIATE")
        except sqlite3.OperationalError:
            raise StoreError("STORE_BUSY") from None
        try:
            result = fn()
            self._conn.execute("COMMIT")
        except Exception:
            if self._conn.in_transaction:
                self._conn.execute("ROLLBACK")
            raise
        if update_head and self._pending_head is not None:
            self._write_head(*self._pending_head)
        return result

    def _require_open_for_work(self) -> None:
        if self.halted:
            raise StoreError("STORE_HALTED")

    # ----------------------------------------------------------------- HEAD
    def _head_path(self) -> str:
        return os.path.join(self.data_root, HEAD_NAME)

    def _write_head(self, seq: int, digest: str) -> None:
        tmp = self._head_path() + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("%d %s\n" % (seq, digest))
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, self._head_path())

    def read_head(self):
        """(seq, hash), None if absent, or "INVALID"."""
        try:
            with open(self._head_path(), "r", encoding="utf-8") as fh:
                text = fh.read()
        except FileNotFoundError:
            return None
        parts = text.strip().split(" ")
        if len(parts) != 2 or not parts[0].isdigit() or len(parts[1]) != 64:
            return "INVALID"
        return int(parts[0]), parts[1]

    # -------------------------------------------------------------- startup
    def _startup(self, now_utc: str, actor: str) -> None:
        result = self.verify()
        head = self.read_head()
        head_repr = list(head) if isinstance(head, tuple) else head
        findings = list(result.problems)
        if result.ok:
            # A halting finding already recorded for this same HEAD keeps its
            # original diagnosis, so recovery is identical on every run.
            last = cj.loads(self._conn.execute(
                "SELECT record FROM audit_log ORDER BY seq DESC LIMIT 1").fetchone()[0])
            detail = last.get("detail") or {}
            if (last.get("event") == "RECOVERY" and detail.get("head") == head_repr
                    and set(detail.get("findings", ())) & self._HALTING):
                self.findings = list(detail["findings"])
                self.halted = True
                return
            if head == "INVALID":
                findings.append("HEAD_INVALID")
            elif head is None:
                findings.append("HEAD_MISSING")
            elif head[0] > result.tail_seq:
                findings.append("AUDIT_TRUNCATION_SUSPECTED")
            elif head[0] == result.tail_seq and head[1] != result.tail_hash:
                findings.append("HEAD_MISMATCH")
            elif head[0] < result.tail_seq:
                findings.append("HEAD_LAG")
        self.findings = findings
        if not findings:
            return
        if not result.ok or self._HALTING & set(findings):
            self.halted = True
        if not result.ok:
            return  # A broken chain cannot be appended to safely.
        # Record the anomaly once. While halted, HEAD is left as found for RK's
        # review (D6); the check above stops a second record for the same HEAD.
        detail = {"findings": sorted(findings), "head": head_repr}
        self._write(lambda: self._append("RECOVERY", now_utc, actor, {"detail": detail}),
                    update_head=not self.halted)

    # ---------------------------------------------------------------- tasks
    def create_task(self, task_id: str, project: str, objective: str,
                    now_utc: str, actor: str, request: Optional[dict] = None) -> int:
        """Create a PENDING task. request, if given, is the structured request
        (capabilities, targets, constraints) kept in the TASK_CREATED record, which
        is the source of truth that later evaluations read."""
        _check_ts(now_utc)
        self._require_open_for_work()
        detail = {"from": None, "to": states.PENDING}
        if request is not None:
            detail["request"] = request

        def fn():
            if self._conn.execute("SELECT 1 FROM tasks WHERE task_id = ?", (task_id,)).fetchone():
                raise StoreError("TASK_EXISTS")
            seq = self._append("TASK_CREATED", now_utc, actor, {
                "task_id": task_id, "project": project, "objective": objective,
                "final_status": states.PENDING,
                "detail": detail,
            })
            self._conn.execute(
                "INSERT INTO tasks VALUES (?, ?, ?, ?, ?, NULL, NULL, NULL, ?, ?, ?, ?, ?)",
                (task_id, project, objective, states.PENDING, Level.L0.value,
                 "NOT_VERIFIED", "OBSERVED", now_utc, now_utc, seq))
            return seq
        return self._write(fn)

    def transition(self, task_id: str, to_state: str, now_utc: str, actor: str,
                   evaluation: Optional[Evaluation] = None,
                   extra: Optional[dict] = None) -> bool:
        """Apply a transition, or record its rejection. Returns True if applied.

        extra may carry files_modified, errors (lists) and detail (a dict merged
        into the record's detail) for the audit record of an applied transition.

        A rejected transition leaves the state unchanged and writes an audit
        event (ADR-0002 D2, test C6).
        """
        _check_ts(now_utc)
        self._require_open_for_work()
        extra = dict(extra or {})
        if not set(extra) <= {"files_modified", "errors", "detail"}:
            raise StoreError("EXTRA_INVALID")

        def fn():
            row = self._conn.execute(
                "SELECT state, project FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
            if row is None:
                raise StoreError("TASK_UNKNOWN")
            from_state, project = row
            ok = states.is_allowed(from_state, to_state)
            used = evaluation if states.needs_evaluation(from_state, to_state) else None
            if ok and states.needs_evaluation(from_state, to_state):
                ok = (used is not None
                      and states.STATE_FOR_OUTCOME.get(used.outcome) == to_state)
            if not ok:
                self._append("TRANSITION_REJECTED", now_utc, actor, {
                    "task_id": task_id, "project": project, "final_status": from_state,
                    "detail": {"from": from_state, "to": to_state},
                })
                return False
            fields = {"task_id": task_id, "project": project, "final_status": to_state,
                      "detail": {"from": from_state, "to": to_state}}
            if used is not None:
                fields.update({
                    "risk_level": used.risk_level.value,
                    "tools_used": sorted(used.capabilities),
                    "detail": {"from": from_state, "to": to_state,
                               "outcome": used.outcome,
                               "policy_version": used.policy_version,
                               "policy_sha256": used.policy_sha256,
                               "contract_sha256": used.contract_sha256,
                               "decisions": [dict(d) for d in used.decisions]},
                })
            for name in ("files_modified", "errors"):
                if name in extra:
                    fields[name] = list(extra[name])
            if "detail" in extra:
                fields["detail"] = dict(fields["detail"], **extra["detail"])
            seq = self._append("TASK_TRANSITION", now_utc, actor, fields)
            if used is not None:
                self._conn.execute(
                    "UPDATE tasks SET state = ?, risk_level = ?, policy_version = ?, "
                    "policy_sha256 = ?, contract_sha256 = ?, updated_utc = ?, last_seq = ? "
                    "WHERE task_id = ?",
                    (to_state, used.risk_level.value, used.policy_version,
                     used.policy_sha256, used.contract_sha256, now_utc, seq, task_id))
            else:
                self._conn.execute(
                    "UPDATE tasks SET state = ?, updated_utc = ?, last_seq = ? WHERE task_id = ?",
                    (to_state, now_utc, seq, task_id))
            return True
        return self._write(fn)

    def get_task(self, task_id: str) -> Optional[dict]:
        cur = self._conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
        row = cur.fetchone()
        if row is None:
            return None
        return dict(zip([c[0] for c in cur.description], row))

    def _task_records(self, task_id: str) -> List[dict]:
        """Every audit record that names the task, oldest first. The SQL filter is
        a cheap pre-selection on the stored bytes; the parsed task_id decides."""
        needle = ('"task_id":%s' % cj.dumps(task_id).decode("utf-8")).encode("utf-8")
        rows = self._conn.execute(
            "SELECT record FROM audit_log WHERE instr(record, ?) > 0 ORDER BY seq",
            (needle,)).fetchall()
        records = [cj.loads(r[0]) for r in rows]
        return [r for r in records if r.get("task_id") == task_id]

    def task_request(self, task_id: str) -> Optional[dict]:
        """The structured request recorded when the task was created, or None."""
        for record in self._task_records(task_id):
            if record.get("event") == "TASK_CREATED":
                return (record.get("detail") or {}).get("request")
        return None

    def task_history(self, task_id: str) -> List[dict]:
        return self._task_records(task_id)

    def known_policy_hashes(self) -> dict:
        """policy_version -> SHA-256 already recorded: the policies in force at
        genesis, then any version a task was evaluated under. A later file with the
        same version and a different hash is POLICY_HASH_MISMATCH (ADR-0003 D6)."""
        known: dict = {}
        genesis = self._conn.execute("SELECT record FROM audit_log WHERE seq = 0").fetchone()
        if genesis:
            for entry in cj.loads(genesis[0]).get("policies", ()):
                known.setdefault(entry["policy_version"], entry["policy_sha256"])
        for version, digest in self._conn.execute(
                "SELECT DISTINCT policy_version, policy_sha256 FROM tasks "
                "WHERE policy_version IS NOT NULL AND policy_sha256 IS NOT NULL ORDER BY policy_version"):
            known.setdefault(version, digest)
        return known

    def list_tasks(self) -> List[dict]:
        cur = self._conn.execute(
            "SELECT task_id, project, state, risk_level, created_utc FROM tasks ORDER BY created_utc, task_id")
        return [dict(zip([c[0] for c in cur.description], row)) for row in cur.fetchall()]

    def count_by_state(self) -> dict:
        return dict(self._conn.execute("SELECT state, COUNT(*) FROM tasks GROUP BY state").fetchall())

    def last_recorded_utc(self) -> Optional[str]:
        row = self._conn.execute(
            "SELECT record FROM audit_log ORDER BY seq DESC LIMIT 1").fetchone()
        return cj.loads(row[0])["timestamp"] if row else None

    # --------------------------------------------------------------- verify
    def verify(self) -> VerifyResult:
        """Walk the chain from genesis (D5). Never re-serializes: re-hashes the
        stored bytes and checks seq and prev_hash inside them."""
        result = VerifyResult(ok=True)
        expected_seq, prev = 0, GENESIS_PREV
        rows = self._conn.execute("SELECT seq, record, record_hash FROM audit_log ORDER BY seq")
        for seq, data, stored_hash in rows:
            if seq != expected_seq:
                result.problems.append("SEQ_GAP at %d" % expected_seq)
                break
            digest = cj.sha256_hex(data)
            if digest != stored_hash:
                result.problems.append("RECORD_HASH_MISMATCH at %d" % seq)
                break
            try:
                record = cj.loads(data)
            except cj.CanonicalError:
                result.problems.append("RECORD_UNPARSEABLE at %d" % seq)
                break
            if record.get("seq") != seq:
                result.problems.append("RECORD_SEQ_MISMATCH at %d" % seq)
                break
            if record.get("prev_hash") != prev:
                result.problems.append("PREV_HASH_MISMATCH at %d" % seq)
                break
            if not all(f in record for f in AUDIT_FIELDS):
                result.problems.append("RECORD_FIELDS_MISSING at %d" % seq)
                break
            if seq == 0 and record.get("event") != "GENESIS":
                result.problems.append("GENESIS_INVALID")
                break
            result.tail_seq, result.tail_hash = seq, digest
            expected_seq, prev = seq + 1, digest
        if result.tail_seq is None and not result.problems:
            result.problems.append("CHAIN_EMPTY")
        result.ok = not result.problems
        return result

    def head_check(self, result: VerifyResult) -> List[str]:
        """Compare HEAD with a verified chain. Regenerates a lagging or missing
        HEAD (D6); reports a HEAD ahead of the chain or a mismatch. A halted
        store reports the diagnosis recorded at start-up."""
        if not result.ok:
            return []
        if self.halted:
            return list(self.findings)
        head = self.read_head()
        if head == "INVALID":
            return ["HEAD_INVALID"]
        if head is not None and head[0] > result.tail_seq:
            return ["AUDIT_TRUNCATION_SUSPECTED"]
        if head is not None and head[0] == result.tail_seq and head[1] != result.tail_hash:
            return ["HEAD_MISMATCH"]
        if head is None or head[0] < result.tail_seq:
            self._write_head(result.tail_seq, result.tail_hash)
        return []
