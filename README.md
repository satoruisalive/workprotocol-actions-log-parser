# gha-log-parser

Parse GitHub Actions workflow logs and return a compact JSON failure summary for CI triage agents.

## Features

- Accepts a GitHub Actions run URL and downloads logs through the GitHub REST API
- Also supports local log files for offline/debug usage
- Extracts:
  - failing step name
  - primary error message
  - stack trace / compiler context
  - GitHub annotation errors
  - suggested fix category: `test`, `build`, `lint`, or `unknown`
- Handles common failure types:
  - pytest / jest-style test failures
  - TypeScript/build errors
  - eslint/pylint/ruff-style lint failures

## Install

```bash
python -m pip install .
```

For development:

```bash
python -m pip install '.[dev]'
```

## Usage

Parse a public or authenticated GitHub Actions run:

```bash
gha-log-parser https://github.com/OWNER/REPO/actions/runs/RUN_ID --pretty
```

For private repos or higher rate limits, provide a token:

```bash
GITHUB_TOKEN=ghp_xxx gha-log-parser https://github.com/OWNER/REPO/actions/runs/RUN_ID --pretty
```

Parse a local log file:

```bash
gha-log-parser --file tests/fixtures/pytest_failure.log --pretty
```

Example output:

```json
{
  "annotations": [],
  "error_message": "FAILED tests/test_math.py::test_addition - AssertionError: assert 3 == 4",
  "failing_step": "pytest",
  "stack_trace": [
    "Traceback (most recent call last):",
    "  File \"tests/test_math.py\", line 4, in test_addition",
    "AssertionError: assert 3 == 4"
  ],
  "suggested_fix_category": "test"
}
```

## Verification

```bash
python -m pytest
python -m pylint gha_log_parser
```

## Notes

GitHub's run log endpoint returns a ZIP archive for full workflow logs. This tool automatically detects ZIP responses, reads contained log files in stable order, and parses the combined text.
