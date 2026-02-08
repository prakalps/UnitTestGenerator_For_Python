"""Basic example module for unit testing."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


def safe_divide(dividend: float, divisor: float) -> float:
    """Divide two numbers, raising ValueError on division by zero."""
    if divisor == 0:
        raise ValueError("divisor cannot be zero")
    return dividend / divisor


def clamp(value: float, minimum: float, maximum: float) -> float:
    """Clamp value within the inclusive [minimum, maximum] range."""
    if minimum > maximum:
        raise ValueError("minimum cannot be greater than maximum")
    if value < minimum:
        return minimum
    if value > maximum:
        return maximum
    return value


@dataclass(frozen=True)
class StringFormatter:
    """Utility class for simple string formatting."""

    suffix: str = ""

    def truncate(self, text: str, max_length: int) -> str:
        """Truncate text to max_length and append suffix if truncated."""
        if max_length < 0:
            raise ValueError("max_length must be non-negative")
        if len(text) <= max_length:
            return text
        truncated = text[:max_length]
        return f"{truncated}{self.suffix}"

    def pad(self, text: str, width: int, fill: str = " ") -> str:
        """Pad text to the desired width using the provided fill character."""
        if len(fill) != 1:
            raise ValueError("fill must be a single character")
        if width <= len(text):
            return text
        return text + (fill * (width - len(text)))


def format_with_timestamp(message: str, now_fn=datetime.now) -> str:
    """Return a message prefixed with the current timestamp."""
    timestamp = now_fn().strftime("%Y-%m-%d %H:%M:%S")
    return f"[{timestamp}] {message}"
