"""Automatic model placement (RK, 2026-11-16, refining Setup A of 2026-11-13).

With the voice on, the model stays on the CPU so the cloned voice has the GPU. With the voice off nothing needs the GPU,
so the server is left to place the model there (measured on this machine: about 45 to 58 tokens/s against 11 on the CPU).
An explicit --num-gpu always wins. The advisor reports where the model really is, from the server, never from its own
assumption. No test here touches the real model.
"""

import http.server
import json
import threading
import unittest

from advisor.__main__ import model_options, placement
from advisor.runtime import ModelUnavailable, OllamaClient


class FakePs(http.server.BaseHTTPRequestHandler):
    models = []
    status = 200

    def log_message(self, *a):
        pass

    def do_GET(self):
        body = json.dumps({"models": FakePs.models}).encode()
        self.send_response(FakePs.status)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class OptionTests(unittest.TestCase):
    def test_voice_on_keeps_the_model_on_the_cpu(self):
        self.assertEqual(model_options(None, r"D:\JARVIS\voice", 0), {"num_gpu": 0})

    def test_voice_off_sets_nothing_so_the_server_uses_the_gpu_as_far_as_memory_allows(self):
        self.assertEqual(model_options(None, None, 0), {})
        self.assertNotIn("num_gpu", model_options(None, "", 0))

    def test_an_explicit_choice_always_wins(self):
        self.assertEqual(model_options(0, None, 0), {"num_gpu": 0})                    # CPU even without voice
        self.assertEqual(model_options(99, r"D:\JARVIS\voice", 0), {"num_gpu": 99})    # GPU even with voice
        self.assertEqual(model_options(20, None, 0), {"num_gpu": 20})                  # partial offload

    def test_threads_are_added_only_when_asked(self):
        self.assertEqual(model_options(None, None, 8), {"num_thread": 8})
        self.assertEqual(model_options(None, "v", 8), {"num_gpu": 0, "num_thread": 8})
        self.assertEqual(model_options(None, None, -1), {})


class PlacementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), FakePs)
        cls.client = OllamaClient(port=cls.server.server_address[1])
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        FakePs.status = 200

    def test_loaded_reports_the_size_and_the_share_in_gpu_memory(self):
        FakePs.models = [{"name": "m:1", "size": 1000, "size_vram": 750, "digest": "x"}]
        self.assertEqual(self.client.loaded(), [{"name": "m:1", "size": 1000, "size_vram": 750}])

    def test_the_placement_line_is_measured_and_gives_the_reason(self):
        FakePs.models = [{"name": "m:1", "size": 6000, "size_vram": 6000}]
        self.assertIn("100% of the model is in GPU memory (automatic: no voice, so the GPU is free)", placement(self.client, "m:1", None, None))
        FakePs.models = [{"name": "m:1", "size": 6000, "size_vram": 0}]
        self.assertIn("0% of the model is in GPU memory (automatic: the voice has the GPU)", placement(self.client, "m:1", None, "voice"))
        self.assertIn("chosen with --num-gpu", placement(self.client, "m:1", 0, None))

    def test_a_partial_placement_is_reported_as_it_is(self):
        FakePs.models = [{"name": "m:1", "size": 6000, "size_vram": 4500}]
        self.assertIn("75% of the model is in GPU memory", placement(self.client, "m:1", None, None))

    def test_a_model_the_server_does_not_list_is_not_claimed(self):
        FakePs.models = [{"name": "other:1", "size": 10, "size_vram": 10}]
        self.assertIn("not reported by the server", placement(self.client, "m:1", None, None))
        FakePs.models = []
        self.assertIn("not reported by the server", placement(self.client, "m:1", None, None))

    def test_an_unreachable_or_failing_server_is_not_claimed_either(self):
        FakePs.status = 500
        self.assertIn("not reported by the server", placement(self.client, "m:1", None, None))
        with self.assertRaises(ModelUnavailable):
            self.client.loaded()
        dead = OllamaClient(port=9)   # nothing listens there
        self.assertIn("not reported by the server", placement(dead, "m:1", None, None))


if __name__ == "__main__":
    unittest.main()
