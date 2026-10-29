"""Parser for test execution logs and verification results."""

import re
from pydantic import BaseModel, Field


class VerificationResult(BaseModel):
    """Normalized result of a dry-run verification."""
    passed: bool
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    error_trace: str = ""
    tests_run: int = 0
    failures: int = 0


class ResultParser:
    """Parses stdout, stderr, and exit codes from verification runs."""

    @staticmethod
    def parse(exit_code: int, stdout: str, stderr: str) -> VerificationResult:
        combined = f"{stdout}\n{stderr}"
        passed = (exit_code == 0)

        # Count tests from pytest summary line (e.g., "1 passed in 0.12s", "1 failed, 2 passed")
        tests_run = 0
        failures = 0
        passed_match = re.search(r"(\d+)\s+passed", combined)
        failed_match = re.search(r"(\d+)\s+failed", combined)
        error_match = re.search(r"(\d+)\s+error", combined)

        if passed_match:
            tests_run += int(passed_match.group(1))
        if failed_match:
            failures += int(failed_match.group(1))
            tests_run += failures
        if error_match:
            failures += int(error_match.group(1))
            tests_run += int(error_match.group(1))

        # Extract traceback if failed
        error_trace = ""
        if not passed:
            # Look for traceback block or FAILURES section
            if "=== FAILURES ===" in combined:
                error_trace = combined.split("=== FAILURES ===")[1]
            elif "Traceback (most recent call last):" in combined:
                parts = combined.split("Traceback (most recent call last):")
                error_trace = "Traceback (most recent call last):" + parts[-1]
            else:
                error_trace = combined[-1500:]  # Last 1500 chars

        return VerificationResult(
            passed=passed,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            error_trace=error_trace.strip(),
            tests_run=tests_run,
            failures=failures,
        )
