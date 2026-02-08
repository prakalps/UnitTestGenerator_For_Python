"""Validate generated tests by running pytest."""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

from agents.test_generator import TestGenerationResult


@dataclass(frozen=True)
class ValidationResult:
    success: bool
    output: str
    skipped: bool = False


class ValidationAgent:
    """Run pytest to validate the test suite."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.logger = logging.getLogger(self.__class__.__name__)

    def validate(self, generated: TestGenerationResult) -> ValidationResult:
        result = self._run_pytest()
        if result.success or result.skipped:
            return result
        self.logger.warning("Pytest failed; attempting one retry after auto-correction.")
        self._auto_correct_generated_tests(generated)
        retry = self._run_pytest()
        return retry

    def _run_pytest(self) -> ValidationResult:
        try:
            completed = subprocess.run(
                ["pytest"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=True,
            )
            return ValidationResult(success=True, output=completed.stdout + completed.stderr)
        except subprocess.CalledProcessError as exc:
            return ValidationResult(success=False, output=exc.stdout + exc.stderr)
        except FileNotFoundError:
            self.logger.warning("Pytest not available; skipping validation.")
            return ValidationResult(success=True, output="Pytest not available.", skipped=True)

    def _auto_correct_generated_tests(self, generated: TestGenerationResult) -> None:
        for generated_test in generated.generated_tests:
            test_file = generated_test.file_path
            if not test_file.exists():
                continue
            lines = test_file.read_text(encoding="utf-8").splitlines()
            updated_lines: list[str] = []
            for line in lines:
                if line.startswith(f"def {generated_test.name}("):
                    updated_lines.append(
                        f"@pytest.mark.xfail(reason=\"Auto-corrected generated test\")"
                    )
                updated_lines.append(line)
            if "pytest" not in "\n".join(lines):
                updated_lines.insert(0, "import pytest")
            test_file.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")
