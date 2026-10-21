"""Store and audit chain: X-04, X-07, X-11, X-15 (ADR-0002 D5), ADR-0005 D1-D6, D12.

Every test uses a temporary data root, never the real one (ADR-0007 D7).
X-05 (two processes) and X-06 (crash injection) need the child-process harness
and are not covered here.
"""

import os
import sqlite3
import tempfile
import unittest

from jarvis import canonical_json as cj
from jarvis import states
from jarvis.reasons import Level
from jarvis.store import AUDIT_FIELDS, Evaluation, Store, StoreError

T0 = "2026-10-21T10:00:00.000000Z"
T1 = "2026-10-21T10:00:01.000000Z"
T2 = "2026-10-21T10:00:02.000000Z"
ACTOR = "tester"
POLICIES = ((1, "a" * 64),)


def evaluation(outcome, level=Level.L2):
    return Evaluation(outcome=outcome, risk_level=level, policy_version=1,
                      policy_sha256="a" * 64, contract_sha256=None,
                      capabilities=("CREATE_TASK",))


class StoreTestCase(unittest.TestCase):
    def setUp(self):
        # Cleanups run last-in first-out: connections opened later close before
        # the store, and the store closes before the directory is removed.
        # Windows cannot delete a database file that is still open.
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = tmp.name
        self.store = Store.create(self.root, T0, ACTOR, POLICIES)
        self.addCleanup(lambda: self.store.close())

    def reopen(self):
        self.store.close()
        self.store = Store.open(self.root, T2, ACTOR)
        return self.store

    def raw(self):
        conn = sqlite3.connect(Store.db_path(self.root), isolation_level=None)
        self.addCleanup(conn.close)
        return conn

    def records(self):
        rows = self.raw().execute("SELECT record FROM audit_log ORDER BY seq").fetchall()
        return [cj.loads(r[0]) for r in rows]


class GenesisAndChainTests(StoreTestCase):
    def test_genesis(self):
        rec = self.records()[0]
        self.assertEqual((rec["seq"], rec["prev_hash"], rec["event"]), (0, "0" * 64, "GENESIS"))
        self.assertEqual(rec["policies"], [{"policy_version": 1, "policy_sha256": "a" * 64}])
        self.assertIn("evaluator_version", rec)
        self.assertIn("schema_versions", rec)

    def test_cannot_create_twice(self):
        with self.assertRaises(StoreError):
            Store.create(self.root, T0, ACTOR, POLICIES)

    def test_chain_links_and_verify_ok(self):
        self.store.create_task("t-1", "jarvis-cp", "first task", T1, ACTOR)
        self.store.transition("t-1", states.RUNNING, T1, ACTOR, evaluation("RUNNABLE"))
        result = self.store.verify()
        self.assertTrue(result.ok, result.problems)
        recs = self.records()
        for prev, cur in zip(recs, recs[1:]):
            self.assertEqual(cur["seq"], prev["seq"] + 1)
        self.assertEqual(result.tail_seq, 2)

    def test_head_tracks_tail(self):
        self.store.create_task("t-1", "jarvis-cp", "x", T1, ACTOR)
        result = self.store.verify()
        self.assertEqual(self.store.read_head(), (result.tail_seq, result.tail_hash))

    def test_head_contains_only_seq_and_hash(self):
        self.store.create_task("t-1", "jarvis-cp", "secret objective text", T1, ACTOR)
        with open(os.path.join(self.root, "HEAD"), "rb") as fh:
            data = fh.read()
        self.assertNotIn(b"secret", data)
        self.assertRegex(data.decode("utf-8"), r"^\d+ [0-9a-f]{64}\n$")


class SchemaCompletenessTests(StoreTestCase):
    """X-15: every section 18 field in every record."""

    def test_every_record_has_every_field(self):
        self.store.create_task("t-1", "jarvis-cp", "x", T1, ACTOR)
        self.store.transition("t-1", states.VERIFIED, T1, ACTOR)
        for rec in self.records():
            for name in AUDIT_FIELDS:
                self.assertIn(name, rec)
            self.assertIn("provenance", rec)
            self.assertEqual(rec["provenance"]["actor"], "OBSERVED")


class TamperTests(StoreTestCase):
    """X-04: altered, deleted, reordered or truncated records are detected."""

    def setUp(self):
        super().setUp()
        for i in range(1, 4):
            self.store.create_task("t-%d" % i, "jarvis-cp", "task %d" % i, T1, ACTOR)
        self.store.close()

    def verify_fresh(self):
        self.store = Store.open(self.root, T2, ACTOR)
        result = self.store.verify()
        return result, self.store.head_check(result), self.store

    def test_altered_record(self):
        conn = self.raw()
        data = conn.execute("SELECT record FROM audit_log WHERE seq = 2").fetchone()[0]
        conn.execute("UPDATE audit_log SET record = ? WHERE seq = 2",
                     (data.replace(b"task 2", b"task X"),))
        result, _, store = self.verify_fresh()
        self.assertFalse(result.ok)
        self.assertTrue(store.halted)

    def test_altered_record_with_recomputed_hash(self):
        conn = self.raw()
        data = conn.execute("SELECT record FROM audit_log WHERE seq = 2").fetchone()[0]
        new = data.replace(b"task 2", b"task X")
        conn.execute("UPDATE audit_log SET record = ?, record_hash = ? WHERE seq = 2",
                     (new, cj.sha256_hex(new)))
        result, _, _ = self.verify_fresh()
        self.assertIn("PREV_HASH_MISMATCH at 3", result.problems)

    def test_deleted_record(self):
        self.raw().execute("DELETE FROM audit_log WHERE seq = 2")
        result, _, _ = self.verify_fresh()
        self.assertIn("SEQ_GAP at 2", result.problems)

    def test_reordered_records(self):
        conn = self.raw()
        a = conn.execute("SELECT record, record_hash FROM audit_log WHERE seq = 1").fetchone()
        b = conn.execute("SELECT record, record_hash FROM audit_log WHERE seq = 2").fetchone()
        conn.execute("UPDATE audit_log SET record = ?, record_hash = ? WHERE seq = 1", b)
        conn.execute("UPDATE audit_log SET record = ?, record_hash = ? WHERE seq = 2", a)
        result, _, _ = self.verify_fresh()
        self.assertIn("RECORD_SEQ_MISMATCH at 1", result.problems)

    def test_truncated_tail(self):
        # tasks.last_seq references the tail; drop the FK link the way a raw
        # edit would, then truncate.
        conn = self.raw()
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("DELETE FROM audit_log WHERE seq = 3")
        result, head_problems, store = self.verify_fresh()
        self.assertTrue(result.ok)
        self.assertIn("AUDIT_TRUNCATION_SUSPECTED", store.findings)
        self.assertTrue(store.halted)
        self.assertEqual(head_problems, ["AUDIT_TRUNCATION_SUSPECTED"])

    def test_truncation_diagnosis_is_stable_across_restarts(self):
        conn = self.raw()
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("DELETE FROM audit_log WHERE seq = 3")
        seen = []
        for _ in range(3):
            store = Store.open(self.root, T2, ACTOR)
            seen.append((tuple(store.findings), store.halted,
                         conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]))
            store.close()
        self.store = Store.open(self.root, T2, ACTOR)
        self.assertEqual(len(set(seen)), 1, seen)
        self.assertEqual(seen[0][:2], (("AUDIT_TRUNCATION_SUSPECTED",), True))

    def test_altered_tail_with_recomputed_hash(self):
        conn = self.raw()
        data = conn.execute("SELECT record FROM audit_log WHERE seq = 3").fetchone()[0]
        new = data.replace(b"task 3", b"task X")
        conn.execute("UPDATE audit_log SET record = ?, record_hash = ? WHERE seq = 3",
                     (new, cj.sha256_hex(new)))
        _, _, store = self.verify_fresh()
        self.assertIn("HEAD_MISMATCH", store.findings)
        self.assertTrue(store.halted)


class RecoveryTests(StoreTestCase):
    def test_lagging_head_is_recorded_and_regenerated(self):
        self.store.create_task("t-1", "jarvis-cp", "x", T1, ACTOR)
        os.remove(os.path.join(self.root, "HEAD"))
        store = self.reopen()
        self.assertEqual(store.findings, ["HEAD_MISSING"])
        self.assertFalse(store.halted)
        self.assertEqual(self.records()[-1]["event"], "RECOVERY")
        result = store.verify()
        self.assertEqual(store.read_head(), (result.tail_seq, result.tail_hash))
        # A clean reopen finds nothing more.
        store = self.reopen()
        self.assertEqual(store.findings, [])

    def test_halted_recovery_is_identical_on_every_run(self):
        self.store.create_task("t-1", "jarvis-cp", "x", T1, ACTOR)
        with open(os.path.join(self.root, "HEAD"), "w", encoding="utf-8", newline="\n") as fh:
            fh.write("99 %s\n" % ("f" * 64))
        counts = []
        for _ in range(3):
            store = self.reopen()
            self.assertTrue(store.halted)
            counts.append(len(self.records()))
        self.assertEqual(counts[0], counts[1])
        self.assertEqual(counts[1], counts[2])
        self.assertEqual(store.read_head(), (99, "f" * 64))

    def test_halted_store_refuses_work(self):
        with open(os.path.join(self.root, "HEAD"), "w", encoding="utf-8", newline="\n") as fh:
            fh.write("99 %s\n" % ("f" * 64))
        store = self.reopen()
        with self.assertRaises(StoreError) as ctx:
            store.create_task("t-9", "jarvis-cp", "x", T2, ACTOR)
        self.assertEqual(ctx.exception.code, "STORE_HALTED")


class TaskStateTests(StoreTestCase):
    def test_restart_keeps_state(self):
        """X-07."""
        self.store.create_task("t-1", "jarvis-cp", "x", T1, ACTOR)
        self.store.transition("t-1", states.DEFERRED, T1, ACTOR, evaluation("DEFERRED", Level.L3))
        before = self.store.get_task("t-1")
        after = self.reopen().get_task("t-1")
        self.assertEqual(before, after)
        self.assertEqual(after["state"], states.DEFERRED)
        self.assertEqual(after["verification"], "NOT_VERIFIED")

    def test_verified_is_rejected_and_audited(self):
        """X-11 (C6)."""
        self.store.create_task("t-1", "jarvis-cp", "x", T1, ACTOR)
        n = len(self.records())
        self.assertFalse(self.store.transition("t-1", states.VERIFIED, T1, ACTOR))
        self.assertEqual(self.store.get_task("t-1")["state"], states.PENDING)
        recs = self.records()
        self.assertEqual(len(recs), n + 1)
        self.assertEqual(recs[-1]["event"], "TRANSITION_REJECTED")
        self.assertEqual(recs[-1]["detail"], {"from": states.PENDING, "to": states.VERIFIED})

    def test_evaluated_transition_requires_matching_evaluation(self):
        self.store.create_task("t-1", "jarvis-cp", "x", T1, ACTOR)
        self.assertFalse(self.store.transition("t-1", states.RUNNING, T1, ACTOR))
        self.assertFalse(self.store.transition("t-1", states.RUNNING, T1, ACTOR,
                                               evaluation("DEFERRED")))
        self.assertTrue(self.store.transition("t-1", states.RUNNING, T1, ACTOR,
                                              evaluation("RUNNABLE")))
        task = self.store.get_task("t-1")
        self.assertEqual((task["state"], task["risk_level"], task["policy_version"]),
                         (states.RUNNING, "L2", 1))

    def test_cancel_is_a_state_change(self):
        self.store.create_task("t-1", "jarvis-cp", "x", T1, ACTOR)
        self.assertTrue(self.store.transition("t-1", states.CANCELLED, T1, ACTOR))
        self.assertFalse(self.store.transition("t-1", states.PENDING, T1, ACTOR))

    def test_unknown_task(self):
        with self.assertRaises(StoreError):
            self.store.transition("nope", states.CANCELLED, T1, ACTOR)

    def test_duplicate_task(self):
        self.store.create_task("t-1", "jarvis-cp", "x", T1, ACTOR)
        with self.assertRaises(StoreError):
            self.store.create_task("t-1", "jarvis-cp", "x", T1, ACTOR)

    def test_failed_write_leaves_no_partial_record(self):
        self.store.create_task("t-1", "jarvis-cp", "x", T1, ACTOR)
        n = len(self.records())
        with self.assertRaises(StoreError):
            self.store.create_task("t-1", "jarvis-cp", "x", T1, ACTOR)
        self.assertEqual(len(self.records()), n)

    def test_last_recorded_utc(self):
        self.store.create_task("t-1", "jarvis-cp", "x", T1, ACTOR)
        self.assertEqual(self.store.last_recorded_utc(), T1)


class WriterLockTests(StoreTestCase):
    """ADR-0005 D2: a second writer that cannot get the lock fails closed."""

    def test_second_writer_fails_closed(self):
        other = sqlite3.connect(Store.db_path(self.root), isolation_level=None)
        self.addCleanup(other.close)
        other.execute("BEGIN IMMEDIATE")
        try:
            self.store.close()
            store = Store.open(self.root, T2, ACTOR, busy_timeout_ms=100)
            self.store = store
            n_before = other.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]
            with self.assertRaises(StoreError) as ctx:
                store.create_task("t-1", "jarvis-cp", "x", T2, ACTOR)
            self.assertEqual(ctx.exception.code, "STORE_BUSY")
        finally:
            other.execute("ROLLBACK")
        self.assertEqual(len(self.records()), n_before)


if __name__ == "__main__":
    unittest.main()
