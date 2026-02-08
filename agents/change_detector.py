"""Detect code changes in src/ using git diff and AST parsing."""

from __future__ import annotations

import ast
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class ChangedSymbol:
    name: str
    symbol_type: str
    file_path: Path
    lineno: int
    end_lineno: int


@dataclass(frozen=True)
class ChangeDetectionResult:
    changed_files: list[Path]
    changed_symbols: list[ChangedSymbol]


class ChangeDetectionAgent:
    """Detect changed Python files and symbols under src/."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.logger = logging.getLogger(self.__class__.__name__)

    def detect_changes(self) -> ChangeDetectionResult:
        changed_files = self._detect_changed_files()
        changed_symbols: list[ChangedSymbol] = []
        for file_path in changed_files:
            changed_symbols.extend(self._detect_changed_symbols(file_path))
        self.logger.info("Detected %s changed file(s).", len(changed_files))
        return ChangeDetectionResult(changed_files=changed_files, changed_symbols=changed_symbols)

    def _detect_changed_files(self) -> list[Path]:
        diff_cmd = ["git", "diff", "--name-only", "HEAD~1", "HEAD"]
        try:
            output = subprocess.check_output(diff_cmd, cwd=self.repo_root, text=True)
        except subprocess.CalledProcessError:
            output = subprocess.check_output(
                ["git", "diff", "--name-only", "HEAD"], cwd=self.repo_root, text=True
            )
        except FileNotFoundError:
            self.logger.warning("Git not available; skipping change detection.")
            return []

        files = [Path(line.strip()) for line in output.splitlines() if line.strip()]
        src_files = [
            self.repo_root / file
            for file in files
            if file.suffix == ".py" and (self.repo_root / "src") in (self.repo_root / file).parents
        ]
        return [file for file in src_files if file.exists()]

    def _detect_changed_symbols(self, file_path: Path) -> Iterable[ChangedSymbol]:
        diff_lines = self._diff_zero_context(file_path)
        candidate_names = self._extract_changed_names(diff_lines)
        symbols = self._parse_symbols(file_path)
        if not candidate_names:
            return symbols
        filtered = [symbol for symbol in symbols if symbol.name in candidate_names]
        return filtered or symbols

    def _diff_zero_context(self, file_path: Path) -> list[str]:
        rel_path = file_path.relative_to(self.repo_root)
        try:
            output = subprocess.check_output(
                ["git", "diff", "-U0", "HEAD~1", "HEAD", "--", str(rel_path)],
                cwd=self.repo_root,
                text=True,
            )
        except subprocess.CalledProcessError:
            output = ""
        return output.splitlines()

    def _extract_changed_names(self, diff_lines: Iterable[str]) -> set[str]:
        names: set[str] = set()
        for line in diff_lines:
            if not line.startswith("+") or line.startswith("+++"):
                continue
            stripped = line.lstrip("+").strip()
            if stripped.startswith("def "):
                name = stripped.split("def ", 1)[1].split("(", 1)[0].strip()
                if name:
                    names.add(name)
            if stripped.startswith("class "):
                name = stripped.split("class ", 1)[1].split("(", 1)[0].split(":", 1)[0].strip()
                if name:
                    names.add(name)
        return names

    def _parse_symbols(self, file_path: Path) -> list[ChangedSymbol]:
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
