"""Command-line interface (ADR-0002 D1 row 9). Record voice only.

This milestone implements `init`, `status`, `audit verify`, `task create`, `task evaluate`,
`task run`, `task show`, `task list`, `report` and `cancel`. `task run` carries a RUNNING
task through its plan to COMPLETED_UNVERIFIED (or FAILED).

Exit codes: 0 ok; 2 usage; 3 configuration error; 4 store missing;
5 audit verification failed or store halted; 6 store busy; 7 task error (bad input,
unknown or existing task, rejected transition); 8 init refused (store exists, data root
missing, policy invalid); 1 unexpected error.
Every unexpected error fails closed.
"""

import argparse
import os
import sys
from datetime import datetime, timezone

from . import config as config_mod
from . import planner
from . import reports
from . import policy as policy_mod
from . import states
from . import tasks as tasks_mod
from .model import PolicyFailure
from .store import Store, StoreError

EXIT_OK, EXIT_UNEXPECTED, EXIT_USAGE = 0, 1, 2
EXIT_CONFIG, EXIT_STORE_MISSING, EXIT_AUDIT, EXIT_BUSY = 3, 4, 5, 6
EXIT_TASK = 7
EXIT_INIT = 8


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


def cmd_init(cfg, args, out) -> int:
    """Create the store and its genesis record in the data root (ADR-0005 D6).

    The data root must already exist: init creates the database and the HEAD file
    only, never a directory. It refuses to touch an existing store."""
    if Store.exists(cfg.data_root):
        _print(out, "init: store already exists")
        return EXIT_INIT
    if not os.path.isdir(cfg.data_root):
        _print(out, "init: data root missing")
        return EXIT_INIT
    loaded = policy_mod.load(args.policy)
    if isinstance(loaded, PolicyFailure):
        _print(out, "init: policy invalid: %s" % loaded.reason)
        return EXIT_INIT
    store = Store.create(cfg.data_root, utc_now(), os_actor(),
                         ((loaded.snapshot.policy_version, loaded.snapshot.sha256),),
                         cfg.busy_timeout_ms)
    try:
        result = store.verify()
        _print(out, "init: OK", "audit_tail_seq: %d" % result.tail_seq,
               "audit_tail_hash: %s" % result.tail_hash,
               "policy_version: %s" % loaded.snapshot.policy_version,
               "policy_sha256: %s" % loaded.snapshot.sha256)
        return EXIT_OK
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


def _open_store(cfg):
    return Store.open(cfg.data_root, utc_now(), os_actor(), cfg.busy_timeout_ms)


def _task_error(out, code) -> int:
    _print(out, "task error: %s" % code)
    return EXIT_TASK


def cmd_task_create(cfg, args, out) -> int:
    try:
        task_id = tasks_mod.validate_id(args.id, "TASK_ID_INVALID")
        project = tasks_mod.validate_id(args.project, "PROJECT_INVALID")
        objective = tasks_mod.validate_objective(args.objective)
        request = tasks_mod.build_request(args.request or [], args.add_capability or [], task_id)
    except tasks_mod.TaskInputError as exc:
        return _task_error(out, exc.code)
    if not Store.exists(cfg.data_root):
        _print(out, "task create: store missing")
        return EXIT_STORE_MISSING
    store = _open_store(cfg)
    try:
        try:
            store.create_task(task_id, project, objective, utc_now(), os_actor(), request)
        except StoreError as exc:
            if exc.code == "TASK_EXISTS":
                return _task_error(out, exc.code)
            raise
        _print(out, "task created: %s" % task_id, "state: %s" % states.PENDING,
               "requests: %d" % len(request["requests"]))
        return EXIT_OK
    finally:
        store.close()


def cmd_task_evaluate(cfg, args, out) -> int:
    if not Store.exists(cfg.data_root):
        _print(out, "task evaluate: store missing")
        return EXIT_STORE_MISSING
    store = _open_store(cfg)
    try:
        task = store.get_task(args.id)
        if task is None:
            return _task_error(out, "TASK_UNKNOWN")
        now = utc_now()
        try:
            evaluation = tasks_mod.evaluate_task(store, cfg, args.policy, args.id, now)
        except tasks_mod.TaskInputError as exc:
            return _task_error(out, exc.code)
        applied = store.transition(args.id, tasks_mod.target_state(evaluation), now,
                                   os_actor(), evaluation)
        for d in evaluation.decisions:
            _print(out, "decision: %s %s %s %s %s" % (
                d["capability"], d["target"], d["verdict"], d["reason"], d["risk_level"]))
        if not applied:
            _print(out, "task evaluate: transition rejected from %s" % task["state"])
            return EXIT_TASK
        _print(out, "task evaluated: %s" % args.id,
               "state: %s" % tasks_mod.target_state(evaluation), "risk: %s" % evaluation.risk_level.value)
        return EXIT_OK
    finally:
        store.close()


def cmd_task_run(cfg, args, out) -> int:
    """Carry a RUNNING task through its plan: in-process, deterministic actions only
    (ADR-0002 D2). RUNNING -> COMPLETED_UNVERIFIED, or FAILED on an error."""
    if not Store.exists(cfg.data_root):
        _print(out, "task run: store missing")
        return EXIT_STORE_MISSING
    store = _open_store(cfg)
    try:
        task = store.get_task(args.id)
        if task is None:
            return _task_error(out, "TASK_UNKNOWN")
        if task["state"] != states.RUNNING:
            return _task_error(out, "TASK_NOT_RUNNING")
        files = []
        try:
            plan = planner.make_plan(store.task_request(args.id))
            for step in plan["steps"]:
                if step["action"] == "WRITE_REPORT":
                    text = reports.render_task_report(store, args.id)
                    files.append(reports.write_task_report(cfg.data_root, args.id, text))
                _print(out, "step %d: %s %s done" % (step["n"], step["capability"], step["action"]))
        except (planner.PlanError, OSError) as exc:
            code = exc.code if isinstance(exc, planner.PlanError) else "ACTION_IO_ERROR"
            store.transition(args.id, states.FAILED, utc_now(), os_actor(),
                             extra={"files_modified": files, "errors": [code]})
            _print(out, "task failed: %s" % args.id, "error: %s" % code)
            return EXIT_TASK
        applied = store.transition(args.id, states.COMPLETED_UNVERIFIED, utc_now(), os_actor(),
                                   extra={"files_modified": files, "detail": {"plan": plan}})
        if not applied:
            return _task_error(out, "TRANSITION_REJECTED")
        _print(out, "task completed: %s" % args.id, "state: %s" % states.COMPLETED_UNVERIFIED,
               "verification: NOT_VERIFIED")
        return EXIT_OK
    finally:
        store.close()


def cmd_report(cfg, args, out) -> int:
    if not Store.exists(cfg.data_root):
        _print(out, "report: store missing")
        return EXIT_STORE_MISSING
    store = _open_store(cfg)
    try:
        if args.id is None:
            out.write(reports.render_summary(store))
            return EXIT_OK
        if store.get_task(args.id) is None:
            return _task_error(out, "TASK_UNKNOWN")
        out.write(reports.render_task_report(store, args.id))
        return EXIT_OK
    finally:
        store.close()


def cmd_task_show(cfg, args, out) -> int:
    if not Store.exists(cfg.data_root):
        _print(out, "task show: store missing")
        return EXIT_STORE_MISSING
    store = _open_store(cfg)
    try:
        task = store.get_task(args.id)
        if task is None:
            return _task_error(out, "TASK_UNKNOWN")
        _print(out, "task: %s" % task["task_id"], "project: %s" % task["project"],
               "state: %s" % task["state"], "risk: %s" % task["risk_level"],
               "policy_version: %s" % task["policy_version"],
               "verification: %s" % task["verification"],
               "created: %s" % task["created_utc"], "updated: %s" % task["updated_utc"])
        for record in store.task_history(args.id):
            detail = record.get("detail") or {}
            _print(out, "event: seq=%d %s %s -> %s" % (
                record["seq"], record["event"], detail.get("from"), detail.get("to")))
            for d in detail.get("decisions", ()):
                _print(out, "  decision: %s %s %s %s" % (
                    d["capability"], d["target"], d["verdict"], d["reason"]))
        return EXIT_OK
    finally:
        store.close()


def cmd_task_list(cfg, out) -> int:
    if not Store.exists(cfg.data_root):
        _print(out, "task list: store missing")
        return EXIT_STORE_MISSING
    store = _open_store(cfg)
    try:
        rows = store.list_tasks()
        for row in rows:
            _print(out, "%s %s %s %s" % (row["task_id"], row["state"], row["risk_level"], row["project"]))
        _print(out, "tasks: %d" % len(rows))
        return EXIT_OK
    finally:
        store.close()


def cmd_cancel(cfg, args, out) -> int:
    """CANCELLED is a state change. It does not stop anything: nothing executes in
    Phase 1 (ADR-0002 D2)."""
    if not Store.exists(cfg.data_root):
        _print(out, "cancel: store missing")
        return EXIT_STORE_MISSING
    store = _open_store(cfg)
    try:
        task = store.get_task(args.id)
        if task is None:
            return _task_error(out, "TASK_UNKNOWN")
        if not store.transition(args.id, states.CANCELLED, utc_now(), os_actor()):
            _print(out, "cancel: transition rejected from %s" % task["state"])
            return EXIT_TASK
        _print(out, "task cancelled: %s" % args.id, "state: %s" % states.CANCELLED)
        return EXIT_OK
    finally:
        store.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="jarvis", description="JARVIS Phase 1 control plane")
    parser.add_argument("--config", default=config_mod.DEFAULT_CONFIG_PATH,
                        help="configuration file in the governance zone")
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="create the store in the data root (first use only)")
    init.add_argument("--policy", default=tasks_mod.DEFAULT_POLICY_PATH,
                      help="policy file whose version and hash go in the genesis record")
    sub.add_parser("status", help="show control-plane status")
    audit = sub.add_parser("audit", help="audit chain operations")
    audit_sub = audit.add_subparsers(dest="audit_command", required=True)
    audit_sub.add_parser("verify", help="verify the audit chain from genesis")

    task = sub.add_parser("task", help="task operations")
    task_sub = task.add_subparsers(dest="task_command", required=True)
    create = task_sub.add_parser("create", help="create a PENDING task")
    create.add_argument("--id", required=True)
    create.add_argument("--project", required=True)
    create.add_argument("--objective", required=True)
    create.add_argument("--request", action="append", metavar="CAPABILITY[=record:TYPE/ID|=path:RAW]",
                        help="a capability the task asks for; repeatable")
    create.add_argument("--add-capability", action="append", metavar="CAPABILITY",
                        help="a constraint that adds a capability: always rejected (CONSTRAINT_WIDENS)")
    evaluate = task_sub.add_parser("evaluate", help="evaluate a task and apply the outcome state")
    evaluate.add_argument("id")
    evaluate.add_argument("--policy", default=tasks_mod.DEFAULT_POLICY_PATH,
                          help="policy file (default: policy/policy.toml in the repository)")
    show = task_sub.add_parser("show", help="show a task and its audit history")
    show.add_argument("id")
    task_sub.add_parser("list", help="list tasks")
    run = task_sub.add_parser("run", help="run a RUNNING task through its plan")
    run.add_argument("id")
    report = sub.add_parser("report", help="print a task report, or a summary with no task id")
    report.add_argument("id", nargs="?")

    cancel = sub.add_parser("cancel", help="move a task to CANCELLED (a state change, not a stop)")
    cancel.add_argument("id")
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
        if args.command == "init":
            return cmd_init(cfg, args, out)
        if args.command == "status":
            return cmd_status(cfg, out)
        if args.command == "audit" and args.audit_command == "verify":
            return cmd_audit_verify(cfg, out)
        if args.command == "task":
            if args.task_command == "create":
                return cmd_task_create(cfg, args, out)
            if args.task_command == "evaluate":
                return cmd_task_evaluate(cfg, args, out)
            if args.task_command == "show":
                return cmd_task_show(cfg, args, out)
            if args.task_command == "list":
                return cmd_task_list(cfg, out)
            if args.task_command == "run":
                return cmd_task_run(cfg, args, out)
        if args.command == "report":
            return cmd_report(cfg, args, out)
        if args.command == "cancel":
            return cmd_cancel(cfg, args, out)
        return EXIT_USAGE
    except StoreError as exc:
        _print(out, "store error: %s" % exc.code)
        return EXIT_BUSY if exc.code == "STORE_BUSY" else EXIT_AUDIT
    except Exception as exc:  # fail closed
        _print(out, "unexpected error: %s" % type(exc).__name__)
        return EXIT_UNEXPECTED
