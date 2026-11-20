"""The model is told the part of the day on every turn, and nothing it is shown denies what the system really does."""

import unittest

from advisor import persona, style_bank
from advisor.conversation import Conversation


class DaypartAndCapabilities(unittest.TestCase):
    def test_every_turn_carries_the_part_of_the_day_when_a_clock_is_given(self):
        c = Conversation(None, "m", {}, persona="P", seed=1)
        c.daypart = lambda: "evening"
        self.assertIn("It is evening here now", c._messages("hello")[0]["content"])

    def test_without_a_clock_nothing_is_added(self):
        c = Conversation(None, "m", {}, persona="P", seed=1)
        self.assertNotIn("here now", c._messages("hello")[0]["content"])

    def test_the_persona_names_what_the_system_does_and_denies_none_of_it(self):
        for text in (persona.PERSONA_TEASING, persona.PERSONA_PLAIN):
            for needle in ("time and date", "notes and to-do list", "weather"):
                self.assertIn(needle, text)

    def test_no_example_says_the_clock_or_the_weather_cannot_be_read(self):
        for question, answer in style_bank.EXCHANGES:
            self.assertNotIn("cannot read the clock", answer)
            self.assertNotIn("cannot see the sky", answer)


if __name__ == "__main__":
    unittest.main()
