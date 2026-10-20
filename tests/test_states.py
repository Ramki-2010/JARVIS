"""Task state machine (ADR-0002 D2)."""

import itertools
import unittest

from jarvis import states as s


class StateMachineTests(unittest.TestCase):
    ALLOWED = {
        (s.PENDING, s.RUNNING), (s.PENDING, s.BLOCKED), (s.PENDING, s.DEFERRED),
        (s.DEFERRED, s.RUNNING), (s.DEFERRED, s.BLOCKED), (s.DEFERRED, s.DEFERRED),
        (s.BLOCKED, s.RUNNING), (s.BLOCKED, s.BLOCKED), (s.BLOCKED, s.DEFERRED),
        (s.RUNNING, s.COMPLETED_UNVERIFIED), (s.RUNNING, s.FAILED),
        (s.PENDING, s.CANCELLED), (s.RUNNING, s.CANCELLED),
        (s.DEFERRED, s.CANCELLED), (s.BLOCKED, s.CANCELLED),
    }

    def test_exact_transition_table(self):
        for a, b in itertools.product(sorted(s.STATES), repeat=2):
            with self.subTest(frm=a, to=b):
                self.assertEqual(s.is_allowed(a, b), (a, b) in self.ALLOWED)

    def test_verified_is_unreachable(self):
        for a in s.STATES:
            self.assertFalse(s.is_allowed(a, s.VERIFIED))

    def test_terminal_states_have_no_exit(self):
        for a, b in itertools.product(s.TERMINAL, s.STATES):
            self.assertFalse(s.is_allowed(a, b))

    def test_leaving_deferred_or_blocked_needs_evaluation(self):
        for a in (s.PENDING, s.DEFERRED, s.BLOCKED):
            for b in (s.RUNNING, s.BLOCKED, s.DEFERRED):
                self.assertTrue(s.needs_evaluation(a, b))
        self.assertFalse(s.needs_evaluation(s.RUNNING, s.COMPLETED_UNVERIFIED))
        self.assertFalse(s.needs_evaluation(s.BLOCKED, s.CANCELLED))


if __name__ == "__main__":
    unittest.main()
