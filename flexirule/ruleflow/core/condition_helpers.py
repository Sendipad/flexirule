"""Small pure helpers exposed to the safe condition evaluator."""

from __future__ import annotations

from typing import Any


def has_outer_whitespace(value: Any) -> bool:
	"""Return whether a string begins or ends with whitespace."""
	return isinstance(value, str) and value != value.strip()
