"""Command-line interface for gha-log-parser."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .github import fetch_run_logs
from .parser import parse_log_text


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Parse GitHub Actions logs into structured failure JSON")
    parser.add_argument("run_url", nargs="?", help="GitHub Actions run URL")
    parser.add_argument("--file", "-f", type=Path, help="Read log text from a local file instead of GitHub")
    parser.add_argument("--token", help="GitHub token; defaults to GITHUB_TOKEN/GH_TOKEN env var")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.file and not args.run_url:
        raise SystemExit("Provide a GitHub Actions run URL or --file")
    if args.file:
        log_text = args.file.read_text(encoding="utf-8", errors="replace")
    else:
        log_text = fetch_run_logs(args.run_url, token=args.token)
    summary = parse_log_text(log_text).to_dict()
    json.dump(summary, sys.stdout, indent=2 if args.pretty else None, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
