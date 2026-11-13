"""Offline time and date (ADR-0014 section 4): fixed zone table, tzdata, no network, no model."""

import unittest
from datetime import datetime, timezone
from unittest import mock

from advisor import clock
from advisor.controller import Controller
from fetcher import keys
from interaction import intents
from interaction.intents import recognise


def at(*args):
    return lambda: datetime(*args, tzinfo=timezone.utc)


class Answers(unittest.TestCase):
    def test_home_time_is_india_time(self):
        shown, spoken = clock.time_text("", at(2026, 11, 13, 17, 12))
        self.assertIn("22:42 IST", shown)
        self.assertEqual(spoken, "It is 10:42 at night, sir.")

    def test_other_zones_and_the_day_difference(self):
        self.assertEqual(clock.time_text("tokyo", at(2026, 11, 13, 17, 12))[1], "In Tokyo it is 2:12 in the morning tomorrow, sir.")
        self.assertEqual(clock.time_text("new york", at(2026, 11, 13, 17, 12))[1], "In New York it is 12:12 in the afternoon, sir.")
        self.assertIn("yesterday", clock.time_text("los angeles", at(2026, 11, 13, 1, 0))[1])

    def test_daylight_saving_is_followed_from_the_zone_data(self):
        self.assertIn("(GMT)", clock.time_text("london", at(2026, 1, 15, 12, 0))[0])
        self.assertIn("(BST)", clock.time_text("london", at(2026, 7, 15, 12, 0))[0])

    def test_morning_noon_and_midnight_are_worded_sensibly(self):
        self.assertEqual(clock.time_text("utc", at(2026, 11, 13, 0, 5))[1], "In UTC it is 12:05 in the morning, sir.")
        self.assertEqual(clock.time_text("utc", at(2026, 11, 13, 12, 30))[1], "In UTC it is 12:30 in the afternoon, sir.")

    def test_the_date(self):
        self.assertEqual(clock.date_text(at(2026, 11, 13, 17, 12))[1], "It is Friday the 13th of November, 2026, sir.")
        self.assertIn("1st", clock.date_text(at(2026, 11, 30, 20, 0))[1])      # 30 Nov 20:00 UTC is 1 December in India
        self.assertIn("11th", clock.date_text(at(2026, 11, 11, 3, 0))[1])
        self.assertIn("22nd", clock.date_text(at(2026, 11, 22, 3, 0))[1])

    def test_every_zone_in_the_table_exists_in_the_zone_data(self):
        for key, (_name, iana, aliases) in keys.ZONES.items():
            with self.subTest(zone=key):
                clock.time_text(key, at(2026, 11, 13, 17, 12))
                self.assertIn(key, aliases)

    def test_missing_zone_data_is_a_clear_failure(self):
        with mock.patch.object(clock, "ZoneInfo", side_effect=KeyError("no tzdata")):
            with self.assertRaises(clock.NoZoneData):
                clock.time_text("", at(2026, 11, 13, 17, 12))


class Routing(unittest.TestCase):
    def test_phrases(self):
        cases = {"what time is it": ("",), "what's the time": ("",), "time": ("",), "what time is it in Tokyo": ("tokyo",),
                 "time in new york right now": ("new york",), "what's the current time in London": ("london",),
                 "what time is it in Narnia": ("?",), "time in Hosur": ("india",), "what's the time in Madras": ("india",)}
        for text, args in cases.items():
            got = recognise(text)
            self.assertEqual((got.kind, got.args), (intents.TIME, args), text)
        for text in ("what's the date", "what day is it", "what's today's date", "what is the day today"):
            self.assertEqual(recognise(text).kind, intents.DATE, text)

    def test_ordinary_talk_is_left_alone(self):
        for text in ("the time is nigh", "I have no time", "time flies", "good day", "day"):
            got = recognise(text)
            self.assertTrue(got is None or got.kind not in (intents.TIME, intents.DATE), text)

    def test_the_conversation_answers_without_the_model_or_any_command(self):
        calls = []
        ctl = Controller(None, lambda a: calls.append(a))   # no model, and the runner must stay unused
        events = list(ctl.respond("what time is it in Dubai"))
        self.assertEqual(calls, [])
        self.assertEqual([k for k, _ in events], ["show", "say"])
        self.assertIn("In Dubai it is", events[1][1])
        self.assertIn("Dubai, Singapore", " ".join(t for _, t in ctl.respond("time in Atlantis")))

    def test_missing_zone_data_gives_a_plain_error_in_conversation(self):
        ctl = Controller(None, lambda a: None)
        with mock.patch.object(clock, "ZoneInfo", side_effect=KeyError("x")):
            events = list(ctl.respond("what time is it"))
        self.assertEqual(events[0][0], "error")
        self.assertIn("no time-zone data", events[0][1])


if __name__ == "__main__":
    unittest.main()
