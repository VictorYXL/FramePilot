import re
from typing import TypedDict

from actions import ActionChunk, ActionStep
from llm_client.base_client import BaseClient


CHUNK_US = 200_000


class GameScalingAction(TypedDict):
    mouse_permille: list[int]
    scroll_notches: int
    held_keys: list[list[str]]


def parse_action(raw: str) -> GameScalingAction:
    match = re.search(r"<\|action_start\|>([^<>]*)<\|action_end\|>", raw)
    if not match:
        raise ValueError("Missing or incomplete action block.")
    mouse, *groups = match[1].split(";")
    values = [int(value) for value in mouse.split()]
    if len(values) != 3 or len(groups) != 6:
        raise ValueError("Expected three mouse values and six key groups.")
    dx, dy, scroll = values
    steps = [group.split() for group in groups]
    if abs(dx) > 1000 or abs(dy) > 1000 or abs(scroll) > 5 or any(len(s) > 4 for s in steps):
        raise ValueError("Action exceeds GameScaling limits.")
    return {"mouse_permille": [dx, dy], "scroll_notches": scroll, "held_keys": steps}


class GameScalingPolicy:
    def __init__(self, client: BaseClient):
        self.client = client

    def reset(self) -> None:
        self.client.reset()

    def act(self, jpeg: bytes, window_size: tuple[int, int]) -> ActionChunk:
        if min(window_size) <= 0:
            raise ValueError("Target window must have positive dimensions.")
        action = parse_action(self.client.predict(jpeg))
        dx, dy = [round(v*n/1000) for v, n in zip(action["mouse_permille"], window_size)]
        steps = action["held_keys"]
        n = len(steps)

        def part(total: int, i: int) -> int:
            # Difference of rounded boundaries preserves the exact signed total.
            return round(total*(i+1)/n) - round(total*i/n)

        return tuple(ActionStep(part(CHUNK_US, i), tuple(keys), part(dx, i), part(dy, i),
                                action["scroll_notches"] if i == 0 else 0)
                     for i, keys in enumerate(steps))
