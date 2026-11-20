import asyncio
import base64
import os
from contextlib import contextmanager
from tempfile import TemporaryDirectory

from .base_client import BaseClient
from .vllm_client import PROMPT


class GitHubCopilotClient(BaseClient):
    def __init__(self, runtime, runner: asyncio.Runner, model: str):
        self.runtime = runtime
        self.runner = runner
        self.model = model

    @classmethod
    @contextmanager
    def open(cls, model: str):
        from copilot import CopilotClient

        with TemporaryDirectory(prefix="framepilot-copilot-") as directory, asyncio.Runner() as runner:
            token = os.environ.get("COPILOT_GITHUB_TOKEN") or None
            runtime = CopilotClient(
                github_token=token, working_directory=directory,
                mode="empty" if token else "copilot-cli",
                base_directory=directory if token else None,
            )
            try:
                runner.run(runtime.start())
                yield cls(runtime, runner, model)
            finally:
                runner.run(runtime.stop())

    def predict(self, jpeg: bytes) -> str:
        return self.runner.run(self._predict(jpeg))

    async def _predict(self, jpeg: bytes) -> str:
        session = await self.runtime.create_session(
            model=self.model, available_tools=[], enable_config_discovery=False,
            enable_skills=False, request_extensions=False, mcp_servers={},
            skip_custom_instructions=True, infinite_sessions={"enabled": False},
            system_message={"mode": "replace", "content": PROMPT},
        )
        try:
            reply = await session.send_and_wait(
                "Predict the action for this game screen. Return only the action block.",
                attachments=[{"type": "blob", "mimeType": "image/jpeg",
                              "data": base64.b64encode(jpeg).decode("ascii")}],
                timeout=180,
            )
            content = getattr(getattr(reply, "data", None), "content", None)
            if not isinstance(content, str) or not content.strip():
                raise ValueError("GitHub Copilot returned no action text.")
            return content
        finally:
            await session.disconnect()
            await self.runtime.delete_session(session.session_id)
