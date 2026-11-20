import sys
import unittest
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gamescaling_policy import GameScalingPolicy
from llm_client.base_client import BaseClient


class GameScalingPolicyTests(unittest.TestCase):
    def test_signed_window_motion_and_key_timing(self):
        client = Mock(spec=BaseClient)
        client.predict.return_value = "<|action_start|>-13 51 -1 ; W ; W LB ; LB ; ; ;<|action_end|>"
        steps = GameScalingPolicy(client).act(b"jpeg", (1280, 720))
        client.predict.assert_called_once_with(b"jpeg")
        self.assertEqual(sum(s.duration_us for s in steps), 200_000)
        self.assertEqual([s.dx for s in steps], [-3, -3, -2, -3, -3, -3])
        self.assertEqual(sum(s.dy for s in steps), 37)
        self.assertEqual([s.held_keys for s in steps], [("W",), ("W", "LB"), ("LB",), (), (), ()])
        self.assertEqual([s.scroll_notches for s in steps], [-1, 0, 0, 0, 0, 0])

    def test_malformed_reply_does_not_produce_executable_steps(self):
        client = Mock(spec=BaseClient)
        client.predict.return_value = "W"
        with self.assertRaisesRegex(ValueError, "action block"):
            GameScalingPolicy(client).act(b"jpeg", (1280, 720))
