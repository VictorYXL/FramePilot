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