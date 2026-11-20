import asyncio
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from llm_client.github_copilot_client import GitHubCopilotClient
from replay import parse_action


class CopilotClientTests(unittest.TestCase):
    def setUp(self):
        self.runner = asyncio.Runner()
        self.addCleanup(self.runner.close)
        self.runtime = AsyncMock()
        self.session = self.runtime.create_session.return_value
        self.session.session_id = "test-frame"
        self.client = GitHubCopilotClient(self.runtime, self.runner, "vision-model")

    def test_frame_attachment_and_existing_parser(self):
        self.session.send_and_wait.return_value = SimpleNamespace(
            data=SimpleNamespace(content="<|action_start|>1 2 0 ; W ; ; ; ; ;<|action_end|>"))
        action = parse_action(self.client.predict(b"frame"))
        self.assertEqual(action["mouse_permille"], [1, 2])
        options = self.runtime.create_session.await_args.kwargs
        self.assertEqual((options["model"], options["available_tools"]), ("vision-model", []))
        attachments = self.session.send_and_wait.await_args.kwargs["attachments"]
        self.assertEqual(attachments, [{"type": "blob", "mimeType": "image/jpeg", "data": "ZnJhbWU="}])
        self.runtime.delete_session.assert_awaited_once_with("test-frame")

    def test_no_reply_is_an_error_and_frame_session_is_cleaned(self):
        self.session.send_and_wait.return_value = None
        with self.assertRaisesRegex(ValueError, "no action text"):
            self.client.predict(b"frame")
        self.session.disconnect.assert_awaited_once()
        self.runtime.delete_session.assert_awaited_once_with("test-frame")
