"""GitHub API client for workflow logs."""

from __future__ import annotations

import io
import os
import re
import zipfile
from dataclasses import dataclass
from urllib.parse import urlparse

import requests


@dataclass(frozen=True, slots=True)
class ActionsRunRef:
    owner: str
    repo: str
    run_id: str


def parse_actions_run_url(url: str) -> ActionsRunRef:
    parsed = urlparse(url)
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 5 or parts[2] != "actions" or parts[3] != "runs":
        raise ValueError("Expected GitHub Actions run URL like https://github.com/OWNER/REPO/actions/runs/RUN_ID")
    return ActionsRunRef(owner=parts[0], repo=parts[1], run_id=parts[4])


def fetch_run_logs(url: str, token: str | None = None) -> str:
    ref = parse_actions_run_url(url)
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "gha-log-parser/0.1.0",
    }
    resolved_token = token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if resolved_token:
        headers["Authorization"] = f"Bearer {resolved_token}"
    api_url = f"https://api.github.com/repos/{ref.owner}/{ref.repo}/actions/runs/{ref.run_id}/logs"
    response = requests.get(api_url, headers=headers, timeout=30)
    response.raise_for_status()
    return _decode_log_response(response.content)


def _decode_log_response(content: bytes) -> str:
    if zipfile.is_zipfile(io.BytesIO(content)):
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            chunks: list[str] = []
            for name in sorted(archive.namelist(), key=_natural_key):
                if name.endswith("/"):
                    continue
                chunks.append(f"\n===== {name} =====\n")
                chunks.append(archive.read(name).decode("utf-8", errors="replace"))
            return "".join(chunks)
    return content.decode("utf-8", errors="replace")


def _natural_key(value: str) -> list[object]:
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", value)]
