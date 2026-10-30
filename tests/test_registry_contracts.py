"""Project registry and contract loaders (ADR-0004 D3 to D9), alone and end to end
through cli.main. Temporary directories only (ADR-0007 D7)."""

import os
import tempfile
import unittest

from jarvis import canonicalizer, contracts, registry
from jarvis.model import ContractFailure, EffectiveContract
from tests.test_tasks_cli import CliCase

OK = "schema_version = 1\n"


def project_block(pid="swarag", name="Swarag", root=None, extra=""):
    lines = ["[[projects]]", 'id = "%s"' % pid, 'name = "%s"' % name]
    if root is not None:
        lines.append("root = '%s'" % root)
    return "\n".join(lines) + "\n" + extra


class RegistryParseTests(unittest.TestCase):
    def parse(self, text):
        return registry.parse(text.encode("utf-8"))

    def test_a_valid_registry_parses_and_a_project_may_have_no_root(self):
        snap = self.parse(OK + project_block(root="D:\\work\\swarag") + project_block("other", "Other"))
        self.assertIsInstance(snap, registry.RegistrySnapshot)
        self.assertEqual([p.id for p in snap.projects], ["swarag", "other"])
        self.assertIsNone(snap.projects[1].root)

    def test_an_empty_registry_is_valid(self):
        self.assertEqual(self.parse(OK + "projects = []\n").projects, ())

    def test_invalid_registries_fail_with_a_closed_code(self):
        cases = {
            "REGISTRY_INVALID": [
                "not toml [",
                OK,  # no projects key
                OK + project_block() + project_block(),  # duplicate id
                OK + project_block("Bad_Id"),
                OK + project_block(root="relative\\path"),
                OK + project_block(extra='allowed_operations = ["PUSH"]\n'),  # unknown key
                OK + "[[projects]]\nid = \"x\"\n",  # no name
            ],
            "REGISTRY_SCHEMA_UNKNOWN": ["schema_version = 2\nprojects = []\n"],
        }
        for code, texts in cases.items():
            for text in texts:
                result = self.parse(text)
                self.assertIsInstance(result, registry.RegistryFailure, text)
                self.assertEqual(result.reason, code, text)

    def test_a_lone_carriage_return_is_invalid(self):
        self.assertIsInstance(registry.parse(b"schema_version = 1\rprojects = []\n"),
                              registry.RegistryFailure)

    def test_missing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(registry.load(os.path.join(tmp, "registry.toml")).reason,
                             "REGISTRY_MISSING")

    def test_crlf_and_lf_give_the_same_hash(self):
        text = OK + project_block()
        a = registry.parse(text.encode())
        b = registry.parse(text.replace("\n", "\r\n").encode())
        self.assertEqual(a.sha256, b.sha256)


class RootRulesTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = os.path.realpath(tmp.name)
        self.gov, self.data, self.repo, self.home = (os.path.join(self.tmp, n) for n in
                                                      ("gov", "data", "repo", "home"))
        for d in (self.gov, self.data, self.repo, self.home):
            os.mkdir(d)
        os.mkdir(os.path.join(self.home, ".claude"))
        self.base = canonicalizer.build_roots(self.gov, self.data, self.repo, self.home,
                                              (".claude",))

    def mkdir(self, *parts):
        path = os.path.join(self.tmp, *parts)
        os.makedirs(path, exist_ok=True)
        return path

    def resolve(self, *blocks):
        snap = registry.parse((OK + "".join(blocks)).encode())
        return registry.resolve_roots(snap, self.base)

    def test_a_good_root_is_usable_and_normalised(self):
        root = self.mkdir("work", "A")
        usable, rejected = self.resolve(project_block(root=root))
        self.assertEqual(usable, {"swarag": canonicalizer.normalize(root)})
        self.assertEqual(rejected, {})

    def test_an_unresolved_root_is_rejected_not_guessed(self):
        usable, rejected = self.resolve(project_block(root=os.path.join(self.tmp, "nowhere")))
        self.assertEqual(usable, {})
        self.assertEqual(rejected, {"swarag": "TARGET_UNRESOLVABLE"})

    def test_protected_areas_cannot_be_registered(self):
        for pid, path in (("gov", self.gov), ("data", self.data), ("repo", self.repo),
                          ("secret", os.path.join(self.home, ".claude")),
                          ("inside", self.mkdir("gov", "sub"))):
            usable, rejected = self.resolve(project_block(pid, pid, path))
            self.assertEqual((usable, rejected), ({}, {pid: "ROOT_PROTECTED"}), pid)

    def test_a_root_that_contains_a_protected_area_is_rejected(self):
        usable, rejected = self.resolve(project_block("wide", "Wide", self.tmp))
        self.assertEqual(rejected, {"wide": "ROOT_PROTECTED"})

    def test_overlapping_roots_are_both_rejected(self):
        outer = self.mkdir("work", "outer")
        inner = self.mkdir("work", "outer", "inner")
        usable, rejected = self.resolve(project_block("outer", "O", outer),
                                        project_block("inner", "I", inner),
                                        project_block("free", "F", self.mkdir("work", "free")))
        self.assertEqual(sorted(rejected), ["inner", "outer"])
        self.assertEqual(set(rejected.values()), {"ROOT_OVERLAP"})
        self.assertEqual(list(usable), ["free"])

    def test_case_differences_do_not_hide_an_overlap(self):
        a = self.mkdir("work", "Case")
        usable, rejected = self.resolve(project_block("a", "A", a),
                                        project_block("b", "B", a.upper()))
        self.assertEqual(sorted(rejected), ["a", "b"])


class ContractParseTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = os.path.realpath(tmp.name)
        self.root = os.path.join(self.tmp, "proj")
        self.src = os.path.join(self.root, "src")
        os.makedirs(self.src)
        self.nested = canonicalizer.normalize(self.root)

    def parse(self, text, pid="swarag"):
        return contracts.parse(text.encode("utf-8"), pid, self.nested)

    def text(self, **over):
        fields = {"schema_version": "1", "project_id": '"swarag"',
                  "scope_roots": "['%s']" % self.src}
        fields.update(over)
        return "".join("%s = %s\n" % kv for kv in fields.items() if kv[1] is not None)

    def test_a_valid_contract_becomes_an_effective_contract(self):
        c = self.parse(self.text(valid_until='"2099-01-01T00:00:00.000000Z"',
                                 protected_paths="['%s']" % os.path.join(self.src, "keys"),
                                 forbidden_operations='["PUSH"]'))
        self.assertIsInstance(c, EffectiveContract)
        self.assertEqual(c.scope_roots, (canonicalizer.normalize(self.src),))
        self.assertEqual(c.forbidden_operations, frozenset({"PUSH"}))
        self.assertEqual(len(c.sha256), 64)
        self.assertEqual(c.valid_until, "2099-01-01T00:00:00.000000Z")

    def test_the_hash_is_over_canonical_bytes(self):
        text = self.text()
        a = contracts.parse(text.encode(), "swarag", self.nested)
        b = contracts.parse(text.replace("\n", "\r\n").encode(), "swarag", self.nested)
        self.assertEqual(a.sha256, b.sha256)

    def test_bad_contracts_fail_closed_with_the_named_reason(self):
        outside = os.path.join(self.tmp, "elsewhere")
        os.mkdir(outside)
        cases = [
            ("CONTRACT_INVALID", "not toml ["),
            ("CONTRACT_INVALID", self.text(extra_key="1")),
            ("CONTRACT_INVALID", self.text(scope_roots=None)),
            ("CONTRACT_INVALID", self.text(project_id='"other"')),
            ("CONTRACT_INVALID", self.text(scope_roots="['%s']" % outside)),  # widens past the root
            ("CONTRACT_INVALID", self.text(scope_roots="['%s']" % self.root.replace("proj", "proj\\.."))),
            ("CONTRACT_INVALID", self.text(scope_roots="['%s']" % os.path.join(self.root, "absent"))),
            ("CONTRACT_INVALID", self.text(valid_until='"tomorrow"')),
            ("CONTRACT_INVALID", self.text(forbidden_operations='["not a capability"]')),
            ("CONTRACT_SCHEMA_UNKNOWN", self.text(schema_version="2")),
        ]
        for reason, text in cases:
            result = self.parse(text)
            self.assertIsInstance(result, ContractFailure, text)
            self.assertEqual(result.reason, reason, text)

    def test_missing_contract(self):
        result = contracts.load(self.tmp, "swarag", self.nested)
        self.assertEqual(result, ContractFailure("CONTRACT_MISSING"))


class EndToEndTests(CliCase):
    """A task with a path target goes through registry, contract and evaluator."""

    def setUp(self):
        super().setUp()
        self.proj = os.path.join(self.tmp, "work", "proj")
        self.src = os.path.join(self.proj, "src")
        os.makedirs(self.src)
        os.makedirs(os.path.join(self.proj, "other"))
        for rel in ("src\\a.txt", "other\\b.txt"):
            with open(os.path.join(self.proj, rel), "w", encoding="utf-8") as fh:
                fh.write("x")
        self.write_text(registry.path_in(self.gov), OK + project_block("p", "P", self.proj))
        self.write_contract()

    def write_text(self, path, text):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)

    def write_contract(self, **over):
        fields = {"schema_version": "1", "project_id": '"p"', "scope_roots": "['%s']" % self.src}
        fields.update(over)
        self.write_text(contracts.path_in(self.gov, "p"),
                        "".join("%s = %s\n" % kv for kv in fields.items()))

    def reason_of(self, target):
        self.create("t1", "READ_FILE=path:%s" % target)
        _, text = self.evaluate()
        return self.reasons(text)[0]

    def test_a_target_in_scope_passes_the_contract_steps(self):
        self.assertEqual(self.reason_of(os.path.join(self.src, "a.txt")), "PHASE_NOT_ENABLED")
        row = self.last_transition()["detail"]
        self.assertEqual(len(row["contract_sha256"]), 64)

    def test_a_target_inside_the_project_but_outside_the_contract_scope_is_denied(self):
        self.assertEqual(self.reason_of(os.path.join(self.proj, "other", "b.txt")),
                         "TARGET_OUT_OF_SCOPE")

    def test_a_forbidden_operation_is_denied(self):
        self.write_contract(forbidden_operations='["READ_FILE"]')
        self.assertEqual(self.reason_of(os.path.join(self.src, "a.txt")), "FORBIDDEN_BY_CONTRACT")

    def test_an_expired_contract_is_denied(self):
        self.write_contract(valid_until='"2000-01-01T00:00:00.000000Z"')
        self.assertNotEqual(self.reason_of(os.path.join(self.src, "a.txt")), "PHASE_NOT_ENABLED")

    def test_no_contract_file_is_contract_missing(self):
        os.remove(contracts.path_in(self.gov, "p"))
        self.assertEqual(self.reason_of(os.path.join(self.src, "a.txt")), "CONTRACT_MISSING")

    def test_an_invalid_contract_is_contract_invalid(self):
        self.write_text(contracts.path_in(self.gov, "p"), "garbage [")
        self.assertEqual(self.reason_of(os.path.join(self.src, "a.txt")), "CONTRACT_INVALID")

    def test_a_missing_registry_denies_project_targets(self):
        os.remove(registry.path_in(self.gov))
        self.assertNotEqual(self.reason_of(os.path.join(self.src, "a.txt")), "PHASE_NOT_ENABLED")

    def test_a_changed_contract_is_seen_on_the_next_evaluation(self):
        target = os.path.join(self.src, "a.txt")
        self.assertEqual(self.reason_of(target), "PHASE_NOT_ENABLED")
        first = self.last_transition()["detail"]["contract_sha256"]
        self.write_contract(forbidden_operations='["READ_FILE"]')
        _, text = self.evaluate()
        self.assertEqual(self.reasons(text), ["FORBIDDEN_BY_CONTRACT"])
        self.assertNotEqual(self.last_transition()["detail"]["contract_sha256"], first)


if __name__ == "__main__":
    unittest.main()
