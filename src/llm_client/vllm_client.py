import base64
from collections import deque

import httpx

from .base_client import BaseClient


PROMPT = """You are playing Valorant from a first-person view. Predict the next 200 ms
of keyboard and mouse input. W/A/S/D move, Space jumps, R reloads, and LB/RB are
mouse buttons. Output <|action_start|>X Y Z ; g1 ; g2 ; g3 ; g4 ; g5 ; g6<|action_end|>.
X and Y are relative mouse motion in thousandths of screen width and height;
Z is scroll notches. Each group lists keys held during one 33 ms step.
An empty group holds no keys. Output the action directly."""


class VLLMClient(BaseClient):
    def __init__(self, http: httpx.Client, model: str = "gamescaling", *,
                 prompt: str = PROMPT, history_len: int = 0):
        self.http = http
        self.model = model
        self.prompt = prompt
        self.history = deque(maxlen=history_len)

    def predict(self, jpeg: bytes) -> str:
        uri = "data:image/jpeg;base64," + base64.b64encode(jpeg).decode("ascii")
        current = {"role": "user", "content": [
            {"type": "text", "text": "current game screen"},
            {"type": "image_url", "image_url": {"url": uri}},
        ]}
        response = self.http.post(
            "chat/completions",
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": self.prompt},
                    *(message for pair in self.history for message in pair),
                    current,
                    {"role": "assistant", "content": "<think>\n\n</think>"},
                ],
                "add_generation_prompt": False,
                "continue_final_message": True,
                "skip_special_tokens": False,
                "stop": ["<|action_end|>"],
                "include_stop_str_in_output": True,
                "temperature": 0,
                "max_tokens": 256,
            },
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        if not isinstance(content, str):
            raise ValueError("Expected a text completion from vLLM.")
        if self.history.maxlen:
            self.history.append((current, {"role": "assistant", "content": content.strip()}))
        return content