"""The conversational voice (ADR-0013 persona review A6.3, RK's review of a real conversation, 2026-11-14).

RK heard: standard replies, "As an artificial intelligence without personal desires or the capacity for love...",
"your kind", "I cannot offer an opinion on such significant life choices", and the same few words ("modest",
"humble") again and again. These tests pin the deterministic parts of the fix: the guard that removes those
constructions, the bank and per-reply hint that widen and vary the vocabulary, and the sampling options. How the
real model behaves is measured separately and reported, not asserted here.
"""

import unittest

from advisor import guard, style_bank
from advisor.controller import Controller
from advisor.conversation import Conversation
from advisor.lines import POOLS
from advisor.persona import PERSONA_PLAIN, PERSONA_TEASING
from advisor.runtime import ModelUnavailable

RKS_REAL_REPLIES = (
    "As an artificial intelligence without personal desires or the capacity for love, I can only observe that such commitments are deeply cherished by humans.",
    "It remains a topic of significant importance to your kind.",
    "That is quite a bold distinction to draw, sir, though I fear I cannot offer an opinion on such significant life choices.",
    "I am operating as JARVIS, sir, a private assistant confined strictly to this laptop.",
)


class GuardTests(unittest.TestCase):
    def test_the_phrases_rk_objected_to_are_removed(self):
        for text in (RKS_REAL_REPLIES[0], RKS_REAL_REPLIES[1], RKS_REAL_REPLIES[2],
                     "As an AI, I do not have feelings.", "I am only a language model, sir.", "I don't have personal opinions, sir.",
                     "That is a matter for you humans, sir.", "How like mankind, sir.", "People like you often ask that, sir.",
                     "I cannot give an opinion on that, sir.", "I do not have desires, sir."):
            self.assertFalse(guard.allowed(text), text)

    def test_ordinary_butler_talk_is_untouched(self):
        for text in ("Marriage is a profound union, sir, and I trust it brings great stability.", RKS_REAL_REPLIES[3],
                     "I am, sir, though I prefer 'staff'.",                      # answering "are you an AI?" lightly is allowed
                     "Quite so. A short ceremony with a good lunch has my vote.", "Humans, sir, are a splendid invention.".replace("Humans", "Chefs")):
            self.assertTrue(guard.allowed(text), text)

    def test_the_bank_teaches_none_of_it(self):
        for question, reply in style_bank.EXCHANGES:
            self.assertTrue(guard.allowed(reply), reply)
        for pool in POOLS.values():
            for phrase in pool:
                self.assertTrue(guard.allowed(phrase), phrase)

    def test_filtered_keeps_the_good_sentences_in_order_and_falls_back_only_when_nothing_is_left(self):
        said = list(guard.filtered(["A fine question, sir.", RKS_REAL_REPLIES[1], "I should say yes."], "FALLBACK"))
        self.assertEqual(said, ["A fine question, sir.", "I should say yes."])
        self.assertEqual(list(guard.filtered(RKS_REAL_REPLIES[:3], "FALLBACK")), ["FALLBACK"])
        self.assertEqual(list(guard.filtered([], "FALLBACK")), ["FALLBACK"])

    def test_scrub_removes_only_the_offending_sentences(self):
        self.assertEqual(guard.scrub("Rather good, sir. It remains a topic for your kind. Do carry on."), "Rather good, sir. Do carry on.")


class ControllerVoiceTests(unittest.TestCase):
    class Conv:
        def __init__(self, reply):
            self.reply = reply

        def stream_reply(self, text):
            yield from self.reply

        def note_exchange(self, a, b):
            pass

    class R:
        code, text, truncated = 0, "", False

    def say(self, reply):
        ctl = Controller(self.Conv(reply), lambda a: self.R(), project="p", tease=False)
        return list(ctl.respond("what do you think about marriage"))

    def test_a_disclaimer_is_never_shown_or_spoken_and_the_rest_is(self):
        events = self.say(["Marriage is a fine thing, sir. ", RKS_REAL_REPLIES[0] + " ", "I wish it every success."])
        self.assertEqual([k for k, _ in events], ["say", "say"])
        text = " ".join(t for _, t in events)
        self.assertNotIn("artificial intelligence", text)
        self.assertIn("fine thing", text)

    def test_a_reply_that_is_all_disclaimer_becomes_a_stock_butler_line(self):
        events = self.say([RKS_REAL_REPLIES[0] + " ", RKS_REAL_REPLIES[1]])
        self.assertEqual(len(events), 1)
        self.assertIn(events[0][1], POOLS["deflect"])

    def test_a_model_that_is_down_is_still_reported_plainly(self):
        class Down:
            def stream_reply(self, text):
                raise ModelUnavailable("x")
                yield

        ctl = Controller(Down(), lambda a: self.R(), project="p", tease=False)
        self.assertEqual(list(ctl.respond("what do you think about marriage"))[0][0], "error")


class VocabularyTests(unittest.TestCase):
    def test_the_bank_is_wide(self):
        self.assertGreaterEqual(len(style_bank.EXCHANGES), 50)
        self.assertGreaterEqual(len(style_bank.PHRASES), 70)
        self.assertGreaterEqual(len(POOLS["joke"]), 20)
        self.assertEqual(len(set(style_bank.PHRASES)), len(style_bank.PHRASES))

    def test_overused_words_are_found_across_recent_replies_and_known_tics_even_once(self):
        replies = ["A modest pleasure, sir, to assist you today.", "Such a modest request, and an easy one.", "Marriage is a profound union, sir."]
        found = style_bank.overused(replies)
        self.assertIn("modest", found)
        self.assertNotIn("marriage", found)
        self.assertIn("humble", style_bank.overused(["A humble house, sir."]))  # a tic even when used once
        self.assertEqual(style_bank.overused([]), [])

    def test_openings_are_reported_once_each(self):
        self.assertEqual(style_bank.openings(["Quite so, sir. Yes.", "Quite so, sir. No.", "Ah, the classic."]), ["quite so", "ah the"])

    def test_the_turn_hint_names_only_what_not_to_repeat_and_is_empty_at_the_start(self):
        """A first version also pushed fresh phrases each turn; measured with the real model, it stuffed them in awkwardly and
        lengthened replies, so only the avoid-lists remain."""
        replies = ["A modest pleasure, sir.", "Such a modest request, sir."]
        self.assertEqual(style_bank.turn_hint(5, 3, replies), style_bank.turn_hint(5, 3, replies))
        self.assertEqual(style_bank.turn_hint(5, 0, []), "")
        hint = style_bank.turn_hint(5, 3, replies)
        self.assertIn("modest", hint)
        self.assertIn("Do not begin with", hint)
        self.assertNotIn("season", hint.lower())
        self.assertLess(len(hint), 400)   # it is paid for on every reply

    def test_the_example_replies_do_not_all_open_alike(self):
        openings = {" ".join(r.split()[:2]).lower() for _q, r in style_bank.EXCHANGES}
        self.assertGreater(len(openings), 35)


class ConversationTests(unittest.TestCase):
    class Client:
        def __init__(self, replies):
            self.replies, self.sent = list(replies), []

        def chat_stream(self, model, messages, options):
            self.sent.append((messages, options))
            yield self.replies.pop(0)

    def test_sampling_is_varied_and_the_hint_follows_the_conversation(self):
        client = self.Client(["A modest pleasure, sir.", "Such a modest request, sir.", "Fine."])
        conv = Conversation(client, "m", {"num_gpu": 0}, persona="PERSONA", seed=3)
        for line in ("hello", "and again", "once more"):
            "".join(conv.stream_reply(line))
        first_messages, options = client.sent[0]
        self.assertEqual(options["num_gpu"], 0)                  # the caller's options still win
        self.assertGreaterEqual(options["temperature"], 0.8)
        self.assertGreater(options["repeat_penalty"], 1.0)
        system_first, system_third = first_messages[0]["content"], client.sent[2][0][0]["content"]
        self.assertTrue(system_first.startswith("PERSONA"))
        self.assertNotIn("overused", system_first)               # nothing to avoid yet
        self.assertIn("modest", system_third)                    # the third reply is told what the first two leaned on
        self.assertNotEqual(system_first, system_third)

    def test_the_scrub_hook_keeps_removed_phrases_out_of_the_models_memory(self):
        client = self.Client(["Quite so, sir. It is a topic for your kind."])
        conv = Conversation(client, "m", persona="P")
        conv.scrub = guard.scrub
        "".join(conv.stream_reply("hello"))
        self.assertEqual(conv.history[-1]["content"], "Quite so, sir.")


class PersonaTextTests(unittest.TestCase):
    def test_the_persona_names_the_tics_and_asks_for_opinions(self):
        for needle in ("your kind", "as an AI", "I cannot offer an opinion", "opinion", "Never open two replies in the same way"):
            self.assertIn(needle, PERSONA_PLAIN)

    def test_the_prompt_no_longer_hands_the_model_the_words_it_was_parroting(self):
        self.assertEqual(PERSONA_PLAIN.lower().count("modest"), 1)   # only inside the 'avoid' list
        for gone in ("a slight difficulty", "as anticipated", "Open with a short phrase of six words or fewer", "internet and I remain"):
            self.assertNotIn(gone, PERSONA_TEASING)

    def test_the_limits_are_stated_once_and_the_lookups_are_acknowledged(self):
        self.assertIn("reads today's weather", PERSONA_PLAIN)
        self.assertNotIn("cannot look anything up live", PERSONA_PLAIN)


if __name__ == "__main__":
    unittest.main()
