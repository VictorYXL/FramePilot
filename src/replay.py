import argparse
import io
import json
import os
import re
import sys
import time
from pathlib import Path

import av
import httpx

from llm_client.base_client import BaseClient
from llm_client.provider import add_provider_args, open_client


CHUNK_US = 200_000


def parse_action(raw: str) -> dict:
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


def decisions(video: Path):
    """Pick the latest frame at or before each decision, in presentation order."""
    with av.open(str(video)) as container:
        stream = container.streams.video[0]
        previous = None
        tick = 0
        for index, frame in enumerate(container.decode(stream)):
            if frame.pts is None:
                raise ValueError(f"Missing presentation timestamp on frame {index}.")
            pts = round(frame.pts * frame.time_base * 1_000_000)
            if previous is None:
                origin = pts
            pts -= origin
            if previous is not None and pts < previous[1]:
                raise ValueError("Non-monotonic video timestamps.")
            while previous is not None and tick < pts:
                yield tick, *previous
                tick += CHUNK_US
            previous = index, pts, frame
        if previous is None:
            raise ValueError("The video contains no frames.")
        last_index, last_pts, last_frame = previous
        if last_frame.duration:
            end = last_pts + round(last_frame.duration * last_frame.time_base * 1_000_000)
        elif stream.duration is not None:
            end = round(stream.duration * stream.time_base * 1_000_000)
        else:
            end = last_pts + 1
        while tick < end:
            yield tick, last_index, last_pts, last_frame
            tick += CHUNK_US


def replay(video: Path, client: BaseClient, output: Path | None = None) -> Path:
    output = output or video.with_suffix(".actions.jsonl")
    partial = output.with_suffix(".jsonl.partial")
    with partial.open("w", encoding="utf-8") as log:
        for tick, index, pts, frame in decisions(video):
            image = io.BytesIO()
            frame.to_image().save(image, format="JPEG", quality=90)
            start = time.perf_counter()
            raw = client.predict(image.getvalue())
            latency = round((time.perf_counter() - start) * 1000, 2)
            try:
                action, error = parse_action(raw), None
            except ValueError as exc:
                action, error = None, str(exc)
            log.write(json.dumps(dict(start_us=tick, end_us=tick + CHUNK_US,
                                      frame_index=index, frame_pts_us=pts, raw=raw,
                                      action=action, parse_error=error, latency_ms=latency)) + "\n")
            log.flush()
    partial.replace(output)
    return output


def main():
    parser = argparse.ArgumentParser(description="Predict actions across a recorded game.")
    parser.add_argument("video", type=Path)
    add_provider_args(parser)
    args = parser.parse_args()
    if not args.video.is_file():
        parser.error(f"Video not found: {args.video}")
    url = os.getenv("FRAMEPILOT_BASE_URL", "http://127.0.0.1:8000/v1")
    try:
        with open_client(args.provider, args.model, url, trust_env=True) as client:
            print(replay(args.video, client))
    except httpx.ConnectError as exc:
        sys.exit(f"Cannot connect to vLLM at {url}: {exc}")


if __name__ == "__main__":
    main()
