import sys
import unittest
from pathlib import Path

if sys.platform != "win32":
    raise unittest.SkipTest("Windows input adapter")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from windows_io import execute


class OutputTests(unittest.TestCase):
    def test_motion_scroll_and_key_transitions(self):
        events = []
        action = dict(mouse_permille=[-13, 51], scroll_notches=-1,
                      held_keys=[["W"], ["W", "LB"], ["LB"], [], [], []])
        execute(action, (1280, 720), lambda: None, events.append, lambda _: None)
        self.assertEqual([(e.data.key.vk, e.data.key.flags) for e in events if e.type],
                         [(87, 0), (87, 2)])
        mouse = [e.data.mouse for e in events if not e.type]
        self.assertEqual((sum(m.dx for m in mouse), sum(m.dy for m in mouse)), (-17, 37))
        self.assertEqual([m.flags for m in mouse if m.flags != 1], [0x800, 2, 4])
        self.assertEqual(mouse[1].data, (-120) % 2**32)

    def test_focus_loss_releases_held_key(self):
        events = []
        def guard():
            if events:
                raise RuntimeError("focus lost")
        with self.assertRaisesRegex(RuntimeError, "focus lost"):
            execute(dict(mouse_permille=[0, 0], scroll_notches=0, held_keys=[["W"]]*6),
                    (100, 100), guard, events.append, lambda _: None)
        self.assertEqual([e.data.key.flags for e in events], [0, 2])
