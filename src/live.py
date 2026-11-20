import argparse
import io
import json
import time
from dataclasses import asdict
from pathlib import Path

from llm_client.provider import add_provider_args, open_client
from gamescaling_policy import GameScalingPolicy
from windows_io import capture, execute, find, foreground, key_state, thread_dpi


def main():
    parser = argparse.ArgumentParser(description="Observe a named Windows window. Input is opt-in.")
    parser.add_argument("--window", required=True, help="Exact top-level window title")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--snapshot", type=Path, help="Save a screenshot and exit without inference")
    mode.add_argument("--execute", action="store_true", help="Send input in an authorized test environment")
    parser.add_argument("--steps", type=int, default=1)
    add_provider_args(parser)
    args = parser.parse_args()
    if args.steps < 1:
        parser.error("--steps must be positive")
    if not thread_dpi(-4):
        parser.error("Cannot initialize per-monitor DPI handling")
    hwnd = find(None, args.window)
    if not hwnd:
        parser.error(f"Window not found: {args.window!r}")

    def guard():
        if key_state(0x7B) & 0x8000 or find(None, args.window) != hwnd or foreground() != hwnd:
            raise RuntimeError("Stopped: F12 held, target changed or window not in foreground.")

    if args.snapshot:
        image = capture(hwnd)
        args.snapshot.parent.mkdir(parents=True, exist_ok=True)
        image.save(args.snapshot)
        print(f"Saved {image.width}x{image.height}: {args.snapshot}")
        return
    if args.execute:
        print("Input armed in 5 seconds. Focus the target; hold F12 or switch away to stop.", flush=True)
        time.sleep(5)
    with open_client(args.provider, args.model, "http://127.0.0.1:8000/v1", trust_env=False) as client:
        policy = GameScalingPolicy(client)
        policy.reset()
        for step in range(args.steps):
            if args.execute:
                guard()
            elif find(None, args.window) != hwnd:
                raise RuntimeError("Target window changed.")
            image = capture(hwnd)
            size = image.size
            jpeg = io.BytesIO()
            image.thumbnail((1280, 720))
            image.save(jpeg, format="JPEG", quality=90)
            start = time.perf_counter()
            chunk = policy.act(jpeg.getvalue(), size)
            print(json.dumps(dict(step=step, inference_ms=round((time.perf_counter()-start)*1000),
                                  steps=[asdict(s) for s in chunk])), flush=True)
            if args.execute:
                execute(chunk, guard)


if __name__ == "__main__":
    main()
