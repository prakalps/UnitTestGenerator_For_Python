# UnitTestGenerator_For_Python

## Directory Structure

```text
.
├── agents/
│   ├── change_detector.py
│   ├── coverage_analyzer.py
│   ├── test_discovery.py
│   ├── test_generator.py
│   └── validator.py
├── ai_test_runner.py
├── scripts/
│   └── git_hooks/
│       ├── post-commit
│       └── pre-commit
├── src/
│   └── <your source modules>.py
└── tests/
    └── test_<module>.py
```

## How to Test the Agent

### Manual Trigger

```bash
python ai_test_runner.py
```

### Install Git Hooks (pre-commit/post-commit)

```bash
python ai_test_runner.py --install-hooks
```

### Notes

- The runner expects source files under `src/` and tests under `tests/`.
- If `pytest` is unavailable, validation will be skipped with a warning.
