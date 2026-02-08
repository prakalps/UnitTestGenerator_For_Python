"""Orchestrate multi-agent unit test generation and validation."""

from __future__ import annotations

import argparse
import importlib.util
import logging
from dataclasses import dataclass
from pathlib import Path

from agents.change_detector import ChangeDetectionAgent
from agents.coverage_analyzer import CoverageAnalyzerAgent
from agents.test_discovery import TestDiscoveryAgent
from agents.test_generator import TestGenerationAgent
from agents.validator import ValidationAgent


@dataclass(frozen=True)
class RunnerConfig:
    coverage_threshold: float = 0.0
    excluded_folders: tuple[str, ...] = ()
    dry_run: bool = False


class AITestRunner:
    """Coordinate change detection, coverage analysis, test generation, and validation."""

    def __init__(self, repo_root: Path, config: RunnerConfig) -> None:
        self.repo_root = repo_root
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.change_detector = ChangeDetectionAgent(repo_root)
        self.test_discovery = TestDiscoveryAgent(repo_root)
        self.coverage_analyzer = CoverageAnalyzerAgent(repo_root)
        self.test_generator = TestGenerationAgent(repo_root)
        self.validator = ValidationAgent(repo_root)

    def run(self) -> int:
        changes = self.change_detector.detect_changes()
        discovery = self.test_discovery.discover_tests()
        coverage = self.coverage_analyzer.analyze(changes)
        if self.config.dry_run:
            self._print_summary(changes, coverage, generated_count=0, validation_success=True)
            return 0

        generated = self.test_generator.generate_tests(coverage, discovery)
        validation = self.validator.validate(generated)

        self._print_summary(
            changes,
            coverage,
            generated_count=len(generated.generated_tests),
            validation_success=validation.success,
        )
        if not validation.success:
            self.logger.error("Validation failed.\n%s", validation.output)
            return 1
        return 0

    def _print_summary(
        self,
        changes,
        coverage,
        generated_count: int,
        validation_success: bool,
    ) -> None:
        print(f"✔ Changed files analyzed: {len(changes.changed_files)}")
        print(f"✔ Coverage gaps found: {len(coverage.gaps)}")
        print(f"✔ New tests generated: {generated_count}")
        status = "✔ All tests passing" if validation_success else "✖ Test validation failed"
        print(status)


def load_config(repo_root: Path) -> RunnerConfig:
    config_path = repo_root / "ai_test_config.yaml"
    if not config_path.exists():
        return RunnerConfig()

    yaml_spec = importlib.util.find_spec("yaml")
    if yaml_spec is None:
        return RunnerConfig()

    yaml = importlib.import_module("yaml")
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    return RunnerConfig(
        coverage_threshold=float(data.get("coverage_threshold", 0.0)),
        excluded_folders=tuple(data.get("excluded_folders", []) or []),
        dry_run=bool(data.get("dry_run", False)),
    )


def install_git_hooks(repo_root: Path) -> None:
    hooks_src = repo_root / "scripts" / "git_hooks"
    hooks_dest = repo_root / ".git" / "hooks"
    hooks_dest.mkdir(parents=True, exist_ok=True)
    for hook_name in ("pre-commit", "post-commit"):
        src = hooks_src / hook_name
        dest = hooks_dest / hook_name
        if src.exists():
            dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
            dest.chmod(0o755)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI test generation runner")
    parser.add_argument("--install-hooks", action="store_true", help="Install git hooks")
    parser.add_argument("--trigger", choices=("manual", "git"), default="manual")
    return parser.parse_args()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    repo_root = Path(__file__).resolve().parent
    args = parse_args()
    if args.install_hooks:
        install_git_hooks(repo_root)
        print("✔ Git hooks installed")
        return 0

    config = load_config(repo_root)
    runner = AITestRunner(repo_root, config)
    return runner.run()


if __name__ == "__main__":
    raise SystemExit(main())
