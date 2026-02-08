"""Analyze coverage and identify gaps for changed symbols."""

from __future__ import annotations

import ast
import json
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

from agents.change_detector import ChangeDetectionResult, ChangedSymbol


@dataclass(frozen=True)
class CoverageGap:
    file: Path
    missing_tests: list[str]


@dataclass(frozen=True)
class CoverageAnalysisResult:
    gaps: list[CoverageGap]
    coverage_json_path: Path | None


class CoverageAnalyzerAgent:
    """Run pytest coverage and identify missing coverage for changed code."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.logger = logging.getLogger(self.__class__.__name__)

    def analyze(self, changes: ChangeDetectionResult) -> CoverageAnalysisResult:
        coverage_json = self._run_coverage()
        if coverage_json is None or not coverage_json.exists():
            self.logger.warning("Coverage data not available.")
            return CoverageAnalysisResult(gaps=[], coverage_json_path=None)

        coverage_data = json.loads(coverage_json.read_text(encoding="utf-8"))
        gaps = self._find_gaps(coverage_data, changes)
        return CoverageAnalysisResult(gaps=gaps, coverage_json_path=coverage_json)

    def _run_coverage(self) -> Path | None:
        coverage_json = self.repo_root / "coverage.json"
        cmd = ["pytest", "--cov=src", "--cov-report=json"]
        try:
            subprocess.run(cmd, cwd=self.repo_root, check=True)
            return coverage_json
        except subprocess.CalledProcessError:
            self.logger.warning("Pytest coverage run failed.")
        except FileNotFoundError:
            self.logger.warning("Pytest not available; skipping coverage.")
        return None

    def _find_gaps(self, coverage_data: dict, changes: ChangeDetectionResult) -> list[CoverageGap]:
        files_data = coverage_data.get("files", {})
        gaps: list[CoverageGap] = []
        for changed_file in changes.changed_files:
            rel_path = str(changed_file.relative_to(self.repo_root))
            file_data = files_data.get(rel_path)
            if not file_data:
                continue
            missing_lines = set(file_data.get("missing_lines", []))
            if not missing_lines:
                continue
            symbols = self._load_symbols(changed_file)
            missing_tests = [
                symbol.name
                for symbol in symbols
                if self._symbol_has_missing_lines(symbol, missing_lines)
            ]
            if missing_tests:
                gaps.append(CoverageGap(file=changed_file, missing_tests=missing_tests))
        return gaps

    def _load_symbols(self, file_path: Path) -> list[ChangedSymbol]:
        content = file_path.read_text(encoding="utf-8")
        parsed = ast.parse(content)
        symbols: list[ChangedSymbol] = []
        for node in ast.walk(parsed):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                end_lineno = getattr(node, "end_lineno", node.lineno)
                symbol_type = "class" if isinstance(node, ast.ClassDef) else "function"
                symbols.append(
                    ChangedSymbol(
                        name=node.name,
                        symbol_type=symbol_type,
                        file_path=file_path,
                        lineno=node.lineno,
                        end_lineno=end_lineno,
                    )
                )
        return symbols

    @staticmethod
    def _symbol_has_missing_lines(symbol: ChangedSymbol, missing_lines: set[int]) -> bool:
        for line in range(symbol.lineno, symbol.end_lineno + 1):
            if line in missing_lines:
                return True
        return False
