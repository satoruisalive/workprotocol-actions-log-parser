from pathlib import Path

from gha_log_parser.github import parse_actions_run_url
from gha_log_parser.parser import parse_log_text

FIXTURES = Path(__file__).parent / "fixtures"


def test_parses_pytest_failure() -> None:
    summary = parse_log_text((FIXTURES / "pytest_failure.log").read_text())
    assert summary.failing_step == "pytest"
    assert summary.suggested_fix_category == "test"
    assert summary.error_message == "FAILED tests/test_math.py::test_addition - AssertionError: assert 3 == 4"
    assert any("tests/test_math.py" in line for line in summary.stack_trace)


def test_parses_typescript_build_failure() -> None:
    summary = parse_log_text((FIXTURES / "typescript_build_failure.log").read_text())
    assert summary.failing_step == "npm run build"
    assert summary.suggested_fix_category == "build"
    assert "TS2322" in (summary.error_message or "")
    assert any("TS2322" in line for line in summary.stack_trace)


def test_parses_lint_annotation() -> None:
    summary = parse_log_text((FIXTURES / "eslint_failure.log").read_text())
    assert summary.failing_step == "eslint ."
    assert summary.suggested_fix_category == "lint"
    assert summary.annotations == [
        {
            "file": "src/app.ts",
            "line": "12",
            "message": "Unexpected console statement. eslint(no-console)",
        }
    ]


def test_parses_github_actions_run_url() -> None:
    ref = parse_actions_run_url("https://github.com/octo-org/octo-repo/actions/runs/123456789")
    assert ref.owner == "octo-org"
    assert ref.repo == "octo-repo"
    assert ref.run_id == "123456789"


def test_rejects_invalid_run_url() -> None:
    try:
        parse_actions_run_url("https://github.com/octo-org/octo-repo/pull/1")
    except ValueError as exc:
        assert "GitHub Actions run URL" in str(exc)
    else:
        raise AssertionError("expected ValueError")
