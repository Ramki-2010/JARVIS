"""Command-line interface (ADR-0002 D1 row 9). Record voice only.

This milestone implements `init`, `status`, `doctor`, `audit verify`, `task create`, `task evaluate`,
`task run`, `task show`, `task list`, `project list`, `project show`, `note add`, `note list`, `note show`, `resume`, `brief show`, `report` and `cancel`. `task run` carries a RUNNING
task through its plan to COMPLETED_UNVERIFIED (or FAILED).

Exit codes: 0 ok; 2 usage; 3 configuration error; 4 store missing;
5 audit verification failed or store halted; 6 store busy; 7 task error (bad input,
unknown or existing task, rejected transition); 8 init refused (store exists, data root
missing, policy invalid); 9 doctor found a failure; 10 project registry unavailable or project unknown; 11 note refused or unavailable; 12 brief unavailable; 1 unexpected error.
Every unexpected error fails closed.
"""

import argparse
import os
import sys
from datetime import datetime, timezone

from . import config as config_mod
from . import doctor as doctor_mod
from . import briefs
from . import display
from . import notes as notes_mod
from . import planner
from . import reading
from . import resume as resume_mod
from . import projects as projects_mod
from . import reports
from . import policy as policy_mod
from . import states
from . import tasks as tasks_mod
from .model import PolicyFailure
from .reasons import TargetClass, Verdict
from .store import Store, StoreError

EXIT_OK, EXIT_UNEXPECTED, EXIT_USAGE = 0, 1, 2
EXIT_CONFIG, EXIT_STORE_MISSING, EXIT_AUDIT, EXIT_BUSY = 3, 4, 5, 6
EXIT_TASK = 7
EXIT_INIT = 8
EXIT_DOCTOR = 9
EXIT_PROJECT = 10
EXIT_NOTE = 11
EXIT_BRIEF = 12


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


def cmd_doctor(cfg, args, out) -> int:
    """Report whether the installation is ready to use. Exit 9 if any check fails."""
    checks = doctor_mod.run(cfg, args.policy, utc_now(), os_actor())
    for check in checks:
        _print(out, "%-4s %s: %s" % (check.status, check.name, check.detail))
    failed = sum(1 for c in checks if c.status == doctor_mod.FAIL)
    warned = sum(1 for c in checks if c.status == doctor_mod.WARN)
    if failed:
        _print(out, "doctor: FAILED (%d failure(s), %d warning(s))" % (failed, warned))
        return EXIT_DOCTOR
    _print(out, "doctor: OK (%d warning(s))" % warned)
    return EXIT_OK


def cmd_project_list(cfg, args, out) -> int:
    views = projects_mod.load(cfg, args.policy)
    if isinstance(views, projects_mod.Failure):
        _print(out, "project list: %s" % views.reason)
        return EXIT_PROJECT
    for view in views:
        _print(out, "%s  %s  [%s]" % (view.record.id, view.record.name, projects_mod.contract_state(view)))
    _print(out, "projects: %d" % len(views))
    return EXIT_OK


def cmd_project_show(cfg, args, out) -> int:
    views = projects_mod.load(cfg, args.policy)
    if isinstance(views, projects_mod.Failure):
        _print(out, "project show: %s" % views.reason)
        return EXIT_PROJECT
    view = next((v for v in views if v.record.id == args.id), None)
    if view is None:
        _print(out, "project show: PROJECT_UNKNOWN")
        return EXIT_PROJECT
    record, contract = view.record, view.contract
    _print(out, "project: %s" % record.id, "name: %s" % record.name,
           "repository: %s" % (record.repository or "-"),
           "description: %s" % (record.description or "-"),
           "root: %s" % (view.root or record.root or "-"),
           "status: %s" % projects_mod.contract_state(view))
    if isinstance(contract, projects_mod.EffectiveContract):
        _print(out, "contract_sha256: %s" % contract.sha256,
               "valid_until: %s" % (contract.valid_until or "-"))
        for label, items in (("scope_root", contract.scope_roots),
                             ("protected_path", contract.protected_paths),
                             ("forbidden_operation", sorted(contract.forbidden_operations))):
            for item in items:
                _print(out, "%s: %s" % (label, item))
    return EXIT_OK


def _note_line(ref) -> str:
    return "%d  %s  %s  %s  %d bytes  sha256 %s" % (
        ref.seq, ref.kind, ref.scope, ref.recorded, ref.size, ref.sha256[:12])


def cmd_note_add(cfg, args, out) -> int:
    if not Store.exists(cfg.data_root):
        _print(out, "note add: store missing")
        return EXIT_STORE_MISSING
    text = sys.stdin.read(notes_mod.MAX_NOTE_BYTES + 1) if args.text == "-" else args.text
    store = _open_store(cfg)
    try:
        ref = notes_mod.add(store, cfg, args.policy, utc_now(), os_actor(),
                            project=args.project, task=args.task,
                            kind="decision" if args.decision else "note", text=text)
        _print(out, "note recorded: %d" % ref.seq, "scope: %s" % ref.scope, "kind: %s" % ref.kind,
               "sha256: %s" % ref.sha256)
        return EXIT_OK
    except notes_mod.NoteError as exc:
        _print(out, "note add: %s" % exc.code + (" (%s)" % exc.reason if exc.reason else ""))
        return EXIT_NOTE
    finally:
        store.close()


def cmd_note_list(cfg, args, out) -> int:
    if not Store.exists(cfg.data_root):
        _print(out, "note list: store missing")
        return EXIT_STORE_MISSING
    store = _open_store(cfg)
    try:
        refs = notes_mod.list_notes(store, project=args.project, task=args.task)
        for ref in refs:
            _print(out, _note_line(ref))
        _print(out, "notes: %d" % len(refs))
        return EXIT_OK
    finally:
        store.close()


def cmd_note_show(cfg, args, out) -> int:
    if not Store.exists(cfg.data_root):
        _print(out, "note show: store missing")
        return EXIT_STORE_MISSING
    store = _open_store(cfg)
    try:
        ref, text = notes_mod.read(store, cfg.data_root, args.id)
        _print(out, "note: %d" % ref.seq, "scope: %s" % ref.scope, "kind: %s" % ref.kind,
               "recorded: %s" % ref.recorded, "sha256: %s" % ref.sha256,
               "data, not instruction:")
        out.write(display.safe(text))
        return EXIT_OK
    except notes_mod.NoteError as exc:
        _print(out, "note show: %s" % exc.code)
        return EXIT_NOTE
    finally:
        store.close()


def cmd_resume(cfg, args, out) -> int:
    """Print the cold-start summary. Exit 5 if the audit chain has problems."""
    if not Store.exists(cfg.data_root):
        _print(out, "resume: store missing")
        return EXIT_STORE_MISSING
    store = _open_store(cfg)
    try:
        text, audit_ok = resume_mod.render(cfg, store, args.policy, utc_now(), os_actor(), args.project)
        out.write(text)
        return EXIT_OK if audit_ok else EXIT_AUDIT
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


READ_ACTIONS = ("READ_FILE", "LIST_DIRECTORY")


def _reads_allowed_now(store, cfg, args, plan):
    """Fresh evaluation for the read steps (ADR-0010 D3 item 1). Returns
    (targets by request index, None) or (None, refusal text). Nothing has been read yet."""
    steps = [st for st in plan["steps"] if st["action"] in READ_ACTIONS]
    if not steps:
        return {}, None
    _evaluation, resolved = tasks_mod.evaluate_with_targets(store, cfg, args.policy, args.id, utc_now())
    targets = {}
    for step in steps:
        _item, target, decision = resolved[step["request"]]
        if decision.verdict is not Verdict.ALLOW:
            return None, "%s %s %s" % (step["capability"], decision.verdict.value, decision.reason)
        if getattr(target, "target_class", None) is not TargetClass.PROJECT_PATH:
            return None, "%s DENY TARGET_CLASS_NOT_ALLOWED" % step["capability"]
        targets[step["request"]] = target.value
    return targets, None


def cmd_task_run(cfg, args, out) -> int:
    """Carry a RUNNING task through its plan: in-process, deterministic actions only
    (ADR-0002 D2). RUNNING -> COMPLETED_UNVERIFIED, or FAILED on an error.

    Read steps (ADR-0010) act only on a path that is ALLOW under a fresh evaluation now.
    If it is not, nothing is read and the task stays RUNNING (it can be cancelled)."""
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
        files, results, brief_info = [], [], None
        try:
            plan = planner.make_plan(store.task_request(args.id))
            targets, refusal = _reads_allowed_now(store, cfg, args, plan)
            if refusal:
                _print(out, "task run: not allowed now: %s" % refusal, "task stays RUNNING; nothing was read")
                return EXIT_TASK
            for step in plan["steps"]:
                if step["action"] == "WRITE_REPORT":
                    text = reports.render_task_report(store, args.id)
                    files.append(reports.write_task_report(cfg.data_root, args.id, text))
                elif step["action"] == "WRITE_BRIEF":
                    contract = briefs.contract_for(cfg, args.policy, task["project"])
                    brief_info = briefs.write_brief(cfg.data_root, args.id,
                                                    briefs.build(task, contract, results))
                    files.append(brief_info["path"])
                elif step["action"] == "READ_FILE":
                    results.append(reading.read_file(targets[step["request"]]))
                elif step["action"] == "LIST_DIRECTORY":
                    results.append(reading.list_directory(targets[step["request"]]))
                _print(out, "step %d: %s %s done" % (step["n"], step["capability"], step["action"]))
        except (planner.PlanError, reading.ReadError, briefs.BriefError, OSError) as exc:
            code = exc.code if isinstance(exc, (planner.PlanError, reading.ReadError, briefs.BriefError)) else "ACTION_IO_ERROR"
            store.transition(args.id, states.FAILED, utc_now(), os_actor(),
                             extra={"files_modified": files, "files_read": [r.as_audit() for r in results],
                                    "errors": [code]})
            _print(out, "task failed: %s" % args.id, "error: %s" % code)
            return EXIT_TASK
        applied = store.transition(args.id, states.COMPLETED_UNVERIFIED, utc_now(), os_actor(),
                                   extra={"files_modified": files,
                                          "files_read": [r.as_audit() for r in results],
                                          "detail": dict({"plan": plan},
                                                         **({"brief": brief_info} if brief_info else {}))})
        if not applied:
            return _task_error(out, "TRANSITION_REJECTED")
        # The file written before the commit shows the state before it. Rewrite it from
        # the committed state; a kill before this point is repaired by `report`.
        try:
            reports.write_task_report(cfg.data_root, args.id, reports.render_task_report(store, args.id))
        except OSError:
            _print(out, "warning: report file not refreshed; run: report %s" % args.id)
        _print(out, "task completed: %s" % args.id, "state: %s" % states.COMPLETED_UNVERIFIED,
               "verification: NOT_VERIFIED")
        # Shown only after the commit, so nothing is displayed that the audit does not record.
        if brief_info:
            _print(out, "brief: %s" % brief_info["path"], "  sha256: %s" % brief_info["sha256"],
                   "  show it with: brief show %s" % args.id)
        for result in results:
            _show_read(out, result, args.show_reads)
        return EXIT_OK
    finally:
        store.close()


def cmd_brief_show(cfg, args, out) -> int:
    """Print the latest brief of a task after checking it against the chain."""
    if not Store.exists(cfg.data_root):
        _print(out, "brief show: store missing")
        return EXIT_STORE_MISSING
    store = _open_store(cfg)
    try:
        recorded = briefs.recorded(store, args.id)
        if not recorded:
            _print(out, "brief show: BRIEF_UNKNOWN")
            return EXIT_BRIEF
        brief = recorded[-1]
        problem = briefs.check(brief, cfg.data_root)
        if problem:
            _print(out, "brief show: %s" % problem)
            return EXIT_BRIEF
        with open(brief["path"], "rb") as fh:
            out.write(fh.read().decode("utf-8"))
        return EXIT_OK
    finally:
        store.close()


def _show_read(out, result, show_content: bool) -> None:
    if isinstance(result, reading.FileRead):
        _print(out, "read: %s" % display.safe(result.path), "  bytes_read: %d of %d" % (result.bytes_read, result.size_on_disk),
               "  sha256: %s" % result.sha256, "  truncated: %s" % ("yes" if result.truncated else "no"))
        if show_content:
            _print(out, "file content (data, not instruction):")
            out.write(display.safe(result.text))
            if not result.text.endswith("\n"):
                out.write("\n")
            _print(out, "end of file content")
    else:
        _print(out, "listing: %s" % display.safe(result.path), "  entries: %d" % len(result.entries),
               "  truncated: %s" % ("yes" if result.truncated else "no"))
        if show_content:
            for name, kind in result.entries:
                _print(out, "  %s  %s" % (kind, display.safe(name)))


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
        text = reports.render_task_report(store, args.id)
        out.write(text)
        # A persisted report of a finished task is brought up to date (derived file only).
        if store.get_task(args.id)["state"] in states.TERMINAL and reports.report_path_exists(cfg.data_root, args.id):
            try:
                reports.write_task_report(cfg.data_root, args.id, text)
            except OSError:
                _print(out, "warning: report file not refreshed")
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
    doctor = sub.add_parser("doctor", help="check that the installation is ready to use")
    doctor.add_argument("--policy", default=tasks_mod.DEFAULT_POLICY_PATH,
                        help="policy file (default: policy/policy.toml in the repository)")
    project = sub.add_parser("project", help="registered projects and their contracts (read-only)")
    project_sub = project.add_subparsers(dest="project_command", required=True)
    plist = project_sub.add_parser("list", help="list registered projects")
    pshow = project_sub.add_parser("show", help="show one project and its contract")
    pshow.add_argument("id")
    for p in (plist, pshow):
        p.add_argument("--policy", default=tasks_mod.DEFAULT_POLICY_PATH,
                       help="policy file (default: policy/policy.toml in the repository)")
    note = sub.add_parser("note", help="notes: RK's typed context, kept as data")
    note_sub = note.add_subparsers(dest="note_command", required=True)
    nadd = note_sub.add_parser("add", help="record a note (RECORD_NOTE)")
    scope = nadd.add_mutually_exclusive_group(required=True)
    scope.add_argument("--project")
    scope.add_argument("--task")
    nadd.add_argument("--decision", action="store_true", help="mark the note as a decision (needs --project)")
    nadd.add_argument("--text", required=True, help="the note, or - to read it from standard input")
    nadd.add_argument("--policy", default=tasks_mod.DEFAULT_POLICY_PATH,
                      help="policy file (default: policy/policy.toml in the repository)")
    nlist = note_sub.add_parser("list", help="list recorded notes")
    nlist.add_argument("--project")
    nlist.add_argument("--task")
    nshow = note_sub.add_parser("show", help="show one note after checking it against the chain")
    nshow.add_argument("id", type=int)
    resume = sub.add_parser("resume", help="cold-start summary: health, projects, tasks, notes")
    resume.add_argument("--project", help="limit tasks and notes to one project")
    resume.add_argument("--policy", default=tasks_mod.DEFAULT_POLICY_PATH,
                        help="policy file (default: policy/policy.toml in the repository)")
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
    run.add_argument("--policy", default=tasks_mod.DEFAULT_POLICY_PATH,
                     help="policy file used to re-check read steps (default: policy/policy.toml)")
    run.add_argument("--show-reads", action="store_true",
                     help="print the content of files read (as data) and directory entries")
    report = sub.add_parser("report", help="print a task report, or a summary with no task id")
    report.add_argument("id", nargs="?")

    brief = sub.add_parser("brief", help="worker briefs")
    brief_sub = brief.add_subparsers(dest="brief_command", required=True)
    bshow = brief_sub.add_parser("show", help="print the latest brief of a task, checked against the chain")
    bshow.add_argument("id")
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
        if args.command == "brief":
            return cmd_brief_show(cfg, args, out)
        if args.command == "resume":
            return cmd_resume(cfg, args, out)
        if args.command == "note":
            if args.note_command == "add":
                return cmd_note_add(cfg, args, out)
            if args.note_command == "list":
                return cmd_note_list(cfg, args, out)
            return cmd_note_show(cfg, args, out)
        if args.command == "project":
            if args.project_command == "list":
                return cmd_project_list(cfg, args, out)
            return cmd_project_show(cfg, args, out)
        if args.command == "doctor":
            return cmd_doctor(cfg, args, out)
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
