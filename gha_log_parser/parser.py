"""Parsing logic for GitHub Actions logs."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Iterable, Literal

FailureCategory = Literal["test", "build", "lint", "unknown"]


@dataclass(slots=True)
class FailureSummary:
    failing_step: str | None
    error_message: str | None
    stack_trace: list[str] = field(default_factory=list)
    suggested_fix_category: FailureCategory = "unknown"
    annotations: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


STEP_PATTERNS = [
    re.compile(r"^##\[group\]Run\s+(?P<step>.+)$"),
    re.compile(r"^##\[group\](?P<step>.+)$"),
    re.compile(r"^##\[section\]Starting:\s*(?P<step>.+)$"),
    re.compile(r"^Run\s+(?P<step>.+)$"),
]
ERROR_PATTERNS = [
    re.compile(r"::error(?:\s+[^:]*)?::(?P<message>.+)$"),
    re.compile(r"^(?P<message>ERROR:.+)$"),
    re.compile(r"^(?P<message>Error:.+)$"),
    re.compile(r"^(?P<message>FAILED\s+.+)$"),
    re.compile(r"^(?P<message>\S+Error:.+)$"),
    re.compile(r"^(?P<message>.*TS\d{4}:.*)$"),
    re.compile(r"^(?P<message>\s*✖\s+.+)$"),
]
ANNOTATION_PATTERN = re.compile(
    r"::error(?:\s+file=(?P<file>[^,]+),line=(?P<line>\d+)[^:]*)?::(?P<message>.+)$"
)


def parse_log_text(text: str) -> FailureSummary:
    lines = text.splitlines()
    step_for_line = _track_steps(lines)
    error_index, error_message = _find_primary_error(lines)
    failing_step = step_for_line.get(error_index) if error_index is not None else _last_step(step_for_line)
    stack_trace = _extract_stack_trace(lines, error_index)
    annotations = _extract_annotations(lines)
    category = _categorize(lines, error_message or "")
    return FailureSummary(
        failing_step=failing_step,
        error_message=error_message,
        stack_trace=stack_trace,
        suggested_fix_category=category,
        annotations=annotations,
    )


def _track_steps(lines: list[str]) -> dict[int, str]:
    current_step: str | None = None
    step_by_line: dict[int, str] = {}
    for idx, line in enumerate(lines):
        for pattern in STEP_PATTERNS:
            match = pattern.match(line.strip())
            if match:
                current_step = _clean(match.group("step"))
                break
        if current_step:
            step_by_line[idx] = current_step
    return step_by_line


def _last_step(step_by_line: dict[int, str]) -> str | None:
    if not step_by_line:
        return None
    return step_by_line[max(step_by_line)]


def _find_primary_error(lines: list[str]) -> tuple[int | None, str | None]:
    for idx, line in enumerate(lines):
        stripped = line.strip()
        for pattern in ERROR_PATTERNS:
            match = pattern.match(stripped)
            if match:
                return idx, _clean(match.group("message"))
    for idx, line in enumerate(lines):
        if "exit code 1" in line.lower() or "process completed with exit code" in line.lower():
            return idx, _clean(line)
    return None, None


def _extract_stack_trace(lines: list[str], error_index: int | None) -> list[str]:
    trace_lines: list[str] = []
    windows: Iterable[tuple[int, int]]
    if error_index is None:
        windows = [(0, len(lines))]
    else:
        windows = [(max(0, error_index - 20), min(len(lines), error_index + 25))]
    stackish = re.compile(
        r"(Traceback \(most recent call last\)|^\s*File \".+\", line \d+|^\s*at .+|"
        r"^\s*\^+\s*$|TS\d{4}:|AssertionError|Error:)"
    )
    for start, end in windows:
        for line in lines[start:end]:
            if stackish.search(line):
                trace_lines.append(line.rstrip())
    return trace_lines[:40]


def _extract_annotations(lines: list[str]) -> list[dict[str, str]]:
    annotations: list[dict[str, str]] = []
    for line in lines:
        match = ANNOTATION_PATTERN.search(line.strip())
        if not match:
            continue
        item = {"message": _clean(match.group("message"))}
        if match.group("file"):
            item["file"] = match.group("file")
        if match.group("line"):
            item["line"] = match.group("line")
        annotations.append(item)
    return annotations


def _categorize(lines: list[str], message: str) -> FailureCategory:
    haystack = "\n".join(lines[-300:]).lower() + "\n" + message.lower()
    if any(token in haystack for token in ["pytest", "jest", "assertionerror", "failed tests", "test failed"]):
        return "test"
    build_tokens = ["tsc", "typescript", "ts230", "ts232", "compilation", "compile", "build failed"]
    if any(token in haystack for token in build_tokens):
        return "build"
    if any(token in haystack for token in ["eslint", "pylint", "ruff", "flake8", "lint", "format"]):
        return "lint"
    return "unknown"


def _clean(value: str) -> str:
    ansi = re.compile(r"\x1b\[[0-9;]*m")
    return ansi.sub("", value).strip()
