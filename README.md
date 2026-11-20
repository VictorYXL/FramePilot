# FramePilot

Predict keyboard and mouse actions for an entire gameplay video. This offline
baseline observes a single frame per decision. It never executes actions or
treats predictions as the recorded player's input history.

## Run

In a vLLM runtime with GPU support, load the checkpoint once. For example, from
the repository root in PowerShell:

```powershell
vllm serve ..\models\GameScaling-0.8B-S3 --served-model-name gamescaling --host 127.0.0.1 --port 8000 --dtype bfloat16 --max-model-len 8192 --max-num-seqs 1
```

Use the checkpoint's own chat template and do not enable a reasoning parser.
The client has separate dependencies and does not require PyTorch or a GPU.
From another terminal in the repository root:

```powershell
uv run --python 3.12 python src\replay.py path\to\gameplay.mp4
```

The default endpoint is `http://127.0.0.1:8000/v1`. To use another trusted
server, set `FRAMEPILOT_BASE_URL`; sampled images are sent to that endpoint.

### Optional GitHub Copilot client

Select `--provider github-copilot --model MODEL_ID` in either replay or live
mode. Use a vision-capable model available to your Copilot account. Authenticate
with the SDK-supported `COPILOT_GITHUB_TOKEN` environment variable or an
existing supported CLI login. FramePilot does not read other projects' token caches.

```powershell
uv run --extra copilot python src\live.py --window "VALORANT" --steps 1 --provider github-copilot --model MODEL_ID
```

This explicitly sends the sampled JPEG and action prompt to GitHub Copilot;
use only images approved for that service. Each frame is a separate model call
and may consume credits. No tools are requested and no previous frames are
included. The response is parsed with the same action parser as vLLM. The
default provider remains vLLM and does not require the Copilot SDK.

## Output

`gameplay.actions.jsonl` is written beside the video. Every 200 ms of video
time, the client selects the latest presented frame and requests one action
chunk. Timestamps are integer microseconds relative to the first presented
frame, not capture-clock timestamps. The last prediction may extend past EOF.
Each line includes the decision interval, frame index and timestamp, raw model
reply, parsed mouse motion (per mille), scroll notches, six groups of held keys,
and request latency in milliseconds. Malformed replies have a null action and
a parse error, not a fabricated no-op. Interrupted runs leave `.jsonl.partial`;
only a completed replay replaces the final output.

## Live Windows window

On Windows 10/11, use the exact title of a restored window. Start with a
snapshot; this does not contact the model or send input:

```powershell
uv run python src\live.py --window "VALORANT" --snapshot output\window.png
uv run python src\live.py --window "VALORANT" --steps 3
```

The second command captures fresh client-area frames, calls the local endpoint
and prints predictions without acting. A game using GPU presentation may
return a blank or stale window capture. Inspect the snapshot before proceeding.
There is no full-desktop fallback.

Only for an application you are authorized to control, add `--execute` to
send standard Windows input. You have five seconds to focus the target. Hold
F12 or switch away to stop before further input; held keys/buttons are
released after each 200 ms chunk. Unsupported keys abort the chunk. A relative
mouse unit is not a calibrated camera angle; Windows settings and the target
application affect the result. Input is not guaranteed to be accepted by a
game. Do not interact with other windows while running this mode.