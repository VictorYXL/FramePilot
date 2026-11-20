import argparse
from contextlib import contextmanager

import httpx

from .vllm_client import VLLMClient


def add_provider_args(parser: argparse.ArgumentParser):
    parser.add_argument("--provider", choices=("vllm", "github-copilot"), default="vllm",
                        help="github-copilot sends each sampled frame to GitHub Copilot")
    parser.add_argument("--model", help="Model ID (required for github-copilot)")


@contextmanager
def open_client(provider: str, model: str | None, url: str, *, trust_env: bool):
    if provider == "github-copilot":
        from .github_copilot_client import GitHubCopilotClient

        if not model:
            raise ValueError("Specify a vision-capable Copilot model using --model.")
        with GitHubCopilotClient.open(model) as client:
            yield client
    elif provider == "vllm":
        with httpx.Client(base_url=url, timeout=180, trust_env=trust_env) as http:
            yield VLLMClient(http, model or "gamescaling")
    else:
        raise ValueError(f"Unknown provider: {provider}")
