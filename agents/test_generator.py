"""Generate pytest tests for uncovered symbols."""

from __future__ import annotations

import ast
import logging
from dataclasses import dataclass
from pathlib import Path

from agents.coverage_analyzer import CoverageAnalysisResult
from agents.test_discovery import TestDiscoveryResult


@dataclass(frozen=True)
class GeneratedTest:
    name: str
    file_path: Path


@dataclass(frozen=True)
class TestGenerationResult:
    generated_tests: list[GeneratedTest]


class TestGenerationAgent:
    """Create tests for uncovered functions or classes."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.logger = logging.getLogger(self.__class__.__name__)

    def generate_tests(
        self,
        coverage: CoverageAnalysisResult,
        discovery: TestDiscoveryResult,
    ) -> TestGenerationResult:
        generated: list[GeneratedTest] = []
        existing_test_names = {
            test_case.name
            for test_cases in discovery.tests_by_file.values()
            for test_case in test_cases
        }
        for gap in coverage.gaps:
            module_path = self._module_path_for_file(gap.file)
            module_alias = self._module_alias(module_path)
            test_file = self._test_file_for_source(gap.file)
            test_file.parent.mkdir(parents=True, exist_ok=True)
            content_lines = []
            if test_file.exists():
                content_lines = test_file.read_text(encoding="utf-8").splitlines()
            else:
                content_lines = ["\"\"\"Auto-generated tests.\"\"\"", "", "import pytest", ""]
            content_lines = self._ensure_module_import(content_lines, module_path, module_alias)

            new_blocks: list[str] = []
            for symbol in self._load_symbols(gap.file):
                if symbol.name not in gap.missing_tests:
                    continue
                test_name = f"test_{symbol.name}"
                if test_name in existing_test_names:
                    continue
                block = self._build_test_block(symbol, module_alias, test_name)
                if block:
                    new_blocks.append(block)
                    generated.append(GeneratedTest(name=test_name, file_path=test_file))

            if new_blocks:
                updated = content_lines + [""] + new_blocks
                test_file.write_text("\n".join(updated).rstrip() + "\n", encoding="utf-8")
        self.logger.info("Generated %s new test(s).", len(generated))
        return TestGenerationResult(generated_tests=generated)

    def _test_file_for_source(self, source_file: Path) -> Path:
        test_name = f"test_{source_file.stem}.py"
        return self.repo_root / "tests" / test_name

    def _module_path_for_file(self, source_file: Path) -> str:
        rel_path = source_file.relative_to(self.repo_root)
        module_parts = rel_path.with_suffix("").parts
        return ".".join(module_parts)

    @staticmethod
    def _module_alias(module_path: str) -> str:
        return f"{module_path.replace('.', '_')}_module"

    def _ensure_module_import(self, lines: list[str], module_path: str, module_alias: str) -> list[str]:
        import_line = f"import {module_path} as {module_alias}"
        if import_line in lines:
            return lines
        insert_index = 0
        for index, line in enumerate(lines):
            if line.startswith("import ") or line.startswith("from "):
                insert_index = index + 1
        updated = lines[:insert_index] + [import_line] + lines[insert_index:]
        return updated

    def _load_symbols(self, source_file: Path) -> list[ast.AST]:
        content = source_file.read_text(encoding="utf-8")
        parsed = ast.parse(content)
        symbols: list[ast.AST] = []
        for node in parsed.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                symbols.append(node)
        return symbols

    def _build_test_block(self, symbol: ast.AST, module_alias: str, test_name: str) -> str | None:
        if isinstance(symbol, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return self._build_function_test(symbol, module_alias, test_name)
        if isinstance(symbol, ast.ClassDef):
            return self._build_class_test(symbol, module_alias, test_name)
        return None

    def _build_function_test(self, symbol: ast.AST, module_alias: str, test_name: str) -> str:
        args = []
        if isinstance(symbol, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = symbol.args.args
        arg_values = [self._default_value(arg.annotation) for arg in args]
        call_args = ", ".join(arg_values)
        if isinstance(symbol, ast.AsyncFunctionDef):
            call_line = f"    result = await {module_alias}.{symbol.name}({call_args})"
        else:
            call_line = f"    result = {module_alias}.{symbol.name}({call_args})"

        lines = [
            f"def {test_name}():",
            f"    \"\"\"Validate {symbol.name} executes with basic inputs.\"\"\"",
            f"    # Arrange",
            f"    # Act",
            call_line,
            f"    # Assert",
            f"    assert result is not None",
        ]
        return "\n".join(lines)

    def _build_class_test(self, symbol: ast.ClassDef, module_alias: str, test_name: str) -> str:
        lines = [
            f"def {test_name}():",
            f"    \"\"\"Ensure {symbol.name} can be instantiated.\"\"\"",
            f"    # Arrange",
            f"    # Act",
            f"    instance = {module_alias}.{symbol.name}()",
            f"    # Assert",
            f"    assert instance is not None",
        ]
        return "\n".join(lines)

    def _default_value(self, annotation: ast.AST | None) -> str:
        if annotation is None:
            return "None"
        if isinstance(annotation, ast.Name):
            return self._default_from_name(annotation.id)
        if isinstance(annotation, ast.Subscript) and isinstance(annotation.value, ast.Name):
            return self._default_from_name(annotation.value.id)
        return "None"

    @staticmethod
    def _default_from_name(name: str) -> str:
        mapping = {
            "int": "0",
            "float": "0.0",
            "str": "\"example\"",
            "bool": "False",
            "list": "[]",
            "dict": "{}",
        }
        return mapping.get(name, "None")
