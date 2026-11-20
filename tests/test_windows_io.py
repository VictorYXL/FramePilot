import sys
import unittest
from pathlib import Path

if sys.platform != "win32":
    raise unittest.SkipTest("Windows input adapter")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from windows_io import execute
from actions import ActionStep


class OutputTests(unittest.TestCase):
    def test_motion_scroll_and_key_transitions(self):
        events = []
        sleeps = []
        chunk = (ActionStep(10_000, ("W",), -17, 37),
                 ActionStep(20_000, ("W", "LB"), scroll_notches=-1),
                 ActionStep(30_000, ("LB",)))
        execute(chunk, lambda: None, events.append, sleeps.append)
        self.assertEqual(sleeps, [.01, .02, .03])
        self.assertEqual([(e.data.key.vk, e.data.key.flags) for e in events if e.type],
                         [(87, 0), (87, 2)])
        mouse = [e.data.mouse for e in events if not e.type]
        self.assertEqual((sum(m.dx for m in mouse), sum(m.dy for m in mouse)), (-17, 37))
        self.assertEqual([m.flags for m in mouse], [1, 2, 0x800, 4])
        self.assertEqual(mouse[2].data, (-120) % 2**32)

    def test_focus_loss_releases_held_key(self):
        events = []
        def guard():
            if events:
                raise RuntimeError("focus lost")
        with self.assertRaisesRegex(RuntimeError, "focus lost"):
            execute((ActionStep(33_333, ("W",)),)*2, guard, events.append, lambda _: None)
        self.assertEqual([e.data.key.flags for e in events], [0, 2])
