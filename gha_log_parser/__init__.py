"""GitHub Actions log parser package."""

from .parser import FailureSummary, parse_log_text

__all__ = ["FailureSummary", "parse_log_text"]
