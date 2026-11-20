from dataclasses import dataclass


@dataclass(frozen=True)
class ActionStep:
    """Relative mouse units scaled to the target window, not normalized deltas."""

    duration_us: int
    held_keys: tuple[str, ...] = ()
    dx: int = 0
    dy: int = 0
    scroll_notches: int = 0

    def __post_init__(self):
        if self.duration_us <= 0:
            raise ValueError("Action duration must be positive.")


type ActionChunk = tuple[ActionStep, ...]
