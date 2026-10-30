"""Task run, report and the planner stub through cli.main (ADR-0002 D1 rows 5 and 9, D2).

Temporary directories only (ADR-0007 D7). Reuses the throwaway store, governance
zone and policy copy of the task-command tests.
"""

import os
import unittest

from jarvis import cli, planner
from tests.test_tasks_cli import CliCase


class PlannerTests(unittest.TestCase):
    def request(self, *caps):
        return {"requests": [{"capability": c} for c in caps]}

    def test_the_plan_is_deterministic_and_ordered_by_capability(self):
        a = planner.make_plan(self.request("CREATE_REPORT", "CREATE_TASK"))
        b = planner.make_plan(self.request("CREATE_TASK", "CREATE_REPORT", "CREATE_TASK"))
        self.assertEqual(a, b)
        self.assertEqual([s["action"] for s in a["steps"]], ["WRITE_REPORT", "RECORD_TASK"])
        self.assertEqual([s["n"] for s in a["steps"]], [1, 2])

    def test_an_unsupported_capability_or_a_missing_request_is_refused(self):
        with self.assertRaises(planner.PlanError) as ctx:
            planner.make_plan(self.request("PUSH"))
        self.assertEqual(ctx.exception.code, "PLAN_CAPABILITY_UNSUPPORTED")
        for bad in (None, {}, {"requests": []}):
            with self.assertRaises(planner.PlanError) as ctx:
                planner.make_plan(bad)
            self.assertEqual(ctx.exception.code, "PLAN_REQUEST_MISSING")


class RunTests(CliCase):
    def running(self, task_id="t1", *requests):
        self.create(task_id, *(requests or ("CREATE_TASK", "CREATE_REPORT")))
        self.evaluate(task_id)
        self.assertEqual(self.state(task_id), "RUNNING")

    def test_run_completes_a_running_task_and_writes_the_report(self):
        self.running()
        code, text = self.run_cli("task", "run", "t1")
        self.assertEqual(code, 0, text)
        self.assertIn("task completed: t1", text)
        self.assertEqual(self.state(), "COMPLETED_UNVERIFIED")
        path = os.path.join(self.data, "reports", "t1.txt")
        with open(path, encoding="utf-8") as fh:
            report = fh.read()
        self.assertIn("state: COMPLETED_UNVERIFIED", report)
        self.assertNotIn("state: RUNNING", report)
        self.assertIn("verification: NOT_VERIFIED", report)
        last = self.last_transition()
        self.assertEqual(last["final_status"], "COMPLETED_UNVERIFIED")
        self.assertEqual(last["files_modified"], [path])
        self.assertEqual([s["action"] for s in last["detail"]["plan"]["steps"]],
                         ["WRITE_REPORT", "RECORD_TASK"])
        self.assertEqual(self.run_cli("audit", "verify")[0], 0)

    def test_run_refuses_a_task_that_is_not_running(self):
        self.create("t1", "CREATE_TASK")
        code, text = self.run_cli("task", "run", "t1")
        self.assertEqual(code, cli.EXIT_TASK)
        self.assertIn("TASK_NOT_RUNNING", text)
        self.assertEqual(self.state(), "PENDING")
        self.assertFalse(os.path.exists(os.path.join(self.data, "reports")))

    def test_run_of_an_unknown_task_is_an_error(self):
        code, text = self.run_cli("task", "run", "nope")
        self.assertEqual(code, cli.EXIT_TASK)
        self.assertIn("TASK_UNKNOWN", text)

    def test_a_completed_task_cannot_run_again_or_be_verified(self):
        self.running()
        self.assertEqual(self.run_cli("task", "run", "t1")[0], 0)
        code, text = self.run_cli("task", "run", "t1")
        self.assertEqual(code, cli.EXIT_TASK)
        self.assertEqual(self.state(), "COMPLETED_UNVERIFIED")

    def test_an_io_error_moves_the_task_to_failed_and_records_it(self):
        self.running()
        blocker = os.path.join(self.data, "reports")
        with open(blocker, "w", encoding="utf-8") as fh:  # a file where the folder must go
            fh.write("x")
        code, text = self.run_cli("task", "run", "t1")
        self.assertEqual(code, cli.EXIT_TASK)
        self.assertIn("task failed: t1", text)
        self.assertEqual(self.state(), "FAILED")
        self.assertEqual(self.last_transition()["errors"], ["ACTION_IO_ERROR"])
        self.assertEqual(self.run_cli("audit", "verify")[0], 0)

    def test_blocked_deferred_and_cancelled_tasks_do_not_run(self):
        self.create("t1", "PUSH")
        self.evaluate("t1")
        self.assertIn(self.state("t1"), ("BLOCKED", "DEFERRED"))
        self.assertEqual(self.run_cli("task", "run", "t1")[0], cli.EXIT_TASK)
        self.running("t2")
        self.assertEqual(self.run_cli("cancel", "t2")[0], 0)
        self.assertEqual(self.run_cli("task", "run", "t2")[0], cli.EXIT_TASK)
        self.assertEqual(self.state("t2"), "CANCELLED")


class ReportTests(CliCase):
    def test_task_report_shows_state_events_and_decisions(self):
        self.create("t1", "CREATE_TASK")
        self.evaluate()
        code, text = self.run_cli("report", "t1")
        self.assertEqual(code, 0, text)
        self.assertIn("task: t1", text)
        self.assertIn("state: RUNNING", text)
        self.assertIn("TASK_CREATED", text)
        self.assertIn("decision: CREATE_TASK", text)
        self.assertNotIn("state: VERIFIED", text)

    def test_summary_report_lists_tasks_and_the_chain_state(self):
        self.create("t1", "CREATE_TASK")
        code, text = self.run_cli("report")
        self.assertEqual(code, 0, text)
        self.assertIn("audit_chain: OK", text)
        self.assertIn("PENDING=1", text)
        self.assertIn("t1 PENDING", text)

    def test_report_is_read_only(self):
        self.create("t1", "CREATE_TASK")
        before = self.records()
        self.run_cli("report", "t1")
        self.run_cli("report")
        self.assertEqual(len(self.records()), len(before))
        self.assertFalse(os.path.exists(os.path.join(self.data, "reports")))

    def test_report_of_an_unknown_task_or_a_missing_store(self):
        self.assertEqual(self.run_cli("report", "nope")[0], cli.EXIT_TASK)
        os.remove(os.path.join(self.data, "jarvis.db"))
        self.assertEqual(self.run_cli("report")[0], cli.EXIT_STORE_MISSING)


if __name__ == "__main__":
    unittest.main()
