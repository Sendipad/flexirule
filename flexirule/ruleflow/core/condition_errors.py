# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

"""Stable, value-safe diagnostics for canonical condition processing."""

from __future__ import annotations


class ConditionError(Exception):
	"""Base error carrying a stable code and structural path, never operand values."""

	default_code = "condition_error"

	def __init__(self, code: str | None = None, path: str = "$", message: str = "Condition error"):
		self.code = code or self.default_code
		self.path = path or "$"
		self.message = message
		super().__init__(f"{self.code} at {self.path}: {self.message}")

	def as_dict(self) -> dict[str, str]:
		"""Return a safe diagnostic suitable for API responses and logs."""
		return {"code": self.code, "path": self.path, "message": self.message}


class ConditionValidationError(ConditionError):
	"""The submitted canonical contract is invalid."""

	default_code = "condition_validation_error"


class ConditionEvaluationError(ConditionError):
	"""A structurally valid condition could not be evaluated safely."""

	default_code = "condition_evaluation_error"
