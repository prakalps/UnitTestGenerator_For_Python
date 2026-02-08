"""Discover existing tests and map source files to test files."""

from __future__ import annotations

import ast
import logging
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TestCaseInfo:
    name: str
    file_path: Path


@dataclass(frozen=True)
class TestDiscoveryResult:
    tests_by_file: dict[Path, list[TestCaseInfo]]


class TestDiscoveryAgent:
    """Scan tests/ for existing test cases."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.tests_root = repo_root / "tests"
        self.logger = logging.getLogger(self.__class__.__name__)

    def discover_tests(self) -> TestDiscoveryResult:
        tests_by_file: dict[Path, list[TestCaseInfo]] = {}
        if not self.tests_root.exists():
            self.logger.info("tests/ directory not found.")
            return TestDiscoveryResult(tests_by_file=tests_by_file)

        for test_file in self.tests_root.rglob("test_*.py"):
            tests_by_file[test_file] = self._parse_test_cases(test_file)
        self.logger.info("Discovered %s test file(s).", len(tests_by_file))
        return TestDiscoveryResult(tests_by_file=tests_by_file)

    def map_source_to_test(self, source_file: Path) -> Path:
        test_name = f"test_{source_file.stem}.py"
        return self.tests_root / test_name

    def _parse_test_cases(self, test_file: Path) -> list[TestCaseInfo]:
        content = test_file.read_text(encoding="utf-8")
        parsed = ast.parse(content)
        cases: list[TestCaseInfo] = []
        for node in ast.walk(parsed):
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                cases.append(TestCaseInfo(name=node.name, file_path=test_file))
            if isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
                for class_node in node.body:
                    if isinstance(class_node, ast.FunctionDef) and class_node.name.startswith("test_"):
                        cases.append(TestCaseInfo(name=f"{node.name}.{class_node.name}", file_path=test_file))
        return cases
