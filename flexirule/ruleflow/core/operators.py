# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

from __future__ import annotations

from typing import Any, ClassVar, Literal, cast

import frappe
from frappe import _


class AssignmentOperator:
	"""Base class for all assignment operators."""

	key: str = ""
	metadata: ClassVar[dict[str, Any]] = {
		"label": "Unknown",
		"requires_value": True,
		"supported_target_types": [],  # Empty means all
		"is_idempotent": False,
	}

	def apply(self, current_value: Any, operand_value: Any, context: dict) -> Any:
		"""
		Apply the operation to the current value.

		Args:
		    current_value: The value currently at the target path.
		    operand_value: The evaluated right-hand side value.
		    context: The execution context (for reference).

		Returns:
		    The new value to be set.
		"""
		raise NotImplementedError

	def validate(self, target_type: str | None, operand_value: Any) -> None:
		"""
		Validate if this operator can be applied to the target and operand.
		Raises MethodExecutionError or ValidationError if invalid.
		"""
		if not self.metadata.get("supported_target_types"):
			return

		if target_type and target_type not in self.metadata["supported_target_types"]:
			frappe.throw(_("Operator '{0}' does not support target type '{1}'").format(self.key, target_type))


class SetOperator(AssignmentOperator):
	key = "set"
	metadata: ClassVar[dict[str, Any]] = {
		"label": "Set Value",
		"requires_value": True,
		"supported_target_types": [],  # All types
		"is_idempotent": True,
	}

	def apply(self, current_value: Any, operand_value: Any, context: dict) -> Any:
		return operand_value


class ClearOperator(AssignmentOperator):
	key = "clear"
	metadata: ClassVar[dict[str, Any]] = {
		"label": "Clear",
		"requires_value": False,
		"supported_target_types": [],  # All types
		"is_idempotent": True,
	}

	def apply(self, current_value: Any, operand_value: Any, context: dict) -> Any:
		# Return sensible defaults based on current value type, or just None
		if isinstance(current_value, list):
			return []
		if isinstance(current_value, dict):
			return {}
		if isinstance(current_value, str):
			return ""
		return None


class IncrementOperator(AssignmentOperator):
	key = "increment"
	metadata: ClassVar[dict[str, Any]] = {
		"label": "Increment By",
		"requires_value": True,
		"supported_target_types": ["Int", "Float", "Currency", "Percent"],
		"is_idempotent": False,
	}

	def apply(self, current_value: Any, operand_value: Any, context: dict) -> Any:
		current = current_value or 0
		operand = operand_value or 0
		try:
			return float(current) + float(operand)
		except (ValueError, TypeError):
			frappe.throw(_("Cannot increment non-numeric values: {0} and {1}").format(current, operand))


class DecrementOperator(AssignmentOperator):
	key = "decrement"
	metadata: ClassVar[dict[str, Any]] = {
		"label": "Decrement By",
		"requires_value": True,
		"supported_target_types": ["Int", "Float", "Currency", "Percent"],
		"is_idempotent": False,
	}

	def apply(self, current_value: Any, operand_value: Any, context: dict) -> Any:
		current = current_value or 0
		operand = operand_value or 0
		try:
			return float(current) - float(operand)
		except (ValueError, TypeError):
			frappe.throw(_("Cannot decrement non-numeric values: {0} and {1}").format(current, operand))


class AppendOperator(AssignmentOperator):
	key = "append"
	metadata: ClassVar[dict[str, Any]] = {
		"label": "Append To List",
		"requires_value": True,
		"supported_target_types": ["Table", "Table MultiSelect"],
		"is_idempotent": False,
	}

	def apply(self, current_value: Any, operand_value: Any, context: dict) -> Any:
		if current_value is None:
			return [operand_value]
		if not isinstance(current_value, list):
			return [current_value, operand_value]

		# Return a new list to ensure ContextManager detects a change and mutations don't leak
		return [*current_value, operand_value]


class MergeOperator(AssignmentOperator):
	key = "merge"
	metadata: ClassVar[dict[str, Any]] = {
		"label": "Merge Object",
		"requires_value": True,
		"supported_target_types": [
			"JSON",
			"Code",
			"Text",
		],  # Typically used on JSON fields or vars dictionaries
		"is_idempotent": False,
	}

	def apply(self, current_value: Any, operand_value: Any, context: dict) -> Any:
		if isinstance(operand_value, str):
			try:
				operand_value = frappe.parse_json(operand_value)
			except Exception:
				pass

		if not isinstance(operand_value, dict):
			frappe.throw(_("Merge operator requires a dictionary as the value"))

		if current_value is None:
			return dict(operand_value)

		if not isinstance(current_value, dict):
			frappe.throw(_("Cannot merge into a non-dictionary target"))

		result = dict(current_value)
		result.update(operand_value)
		return result


class ToggleOperator(AssignmentOperator):
	key = "toggle"
	metadata: ClassVar[dict[str, Any]] = {
		"label": "Toggle Boolean",
		"requires_value": False,
		"supported_target_types": ["Check"],
		"is_idempotent": False,
	}

	def apply(self, current_value: Any, operand_value: Any, context: dict) -> Any:
		# Convert common Frappe boolean equivalents (1/0, "Yes"/"No", True/False)
		val = current_value
		if isinstance(val, str):
			val = val.lower() == "yes" or val.lower() == "true" or val == "1"
		elif isinstance(val, int):
			val = bool(val)

		# If it's falsy, return True (1), if truthy return False (0) for Frappe Check fields
		return 0 if val else 1


class AssignmentOperatorRegistry:
	"""Registry for assignment operators."""

	_registry: ClassVar[dict[str, AssignmentOperator]] = {}
	_initialized: ClassVar[bool] = False

	@classmethod
	def register(cls, operator: AssignmentOperator) -> None:
		cls._registry[operator.key] = operator

	@classmethod
	def _ensure_initialized(cls) -> None:
		if cls._initialized:
			return

		cls.register(SetOperator())
		cls.register(ClearOperator())
		cls.register(IncrementOperator())
		cls.register(DecrementOperator())
		cls.register(AppendOperator())
		cls.register(MergeOperator())
		cls.register(ToggleOperator())

		cls._initialized = True

	@classmethod
	def get(cls, operator_key: str) -> AssignmentOperator:
		cls._ensure_initialized()
		op = cls._registry.get(operator_key)
		if not op:
			frappe.throw(_("Unknown assignment operator: {0}").format(operator_key))
		return cast("AssignmentOperator", op)

	@classmethod
	def get_metadata_map(cls) -> dict[str, dict[str, Any]]:
		"""Return a mapping of operator keys to their frontend metadata."""
		cls._ensure_initialized()
		return {key: op.metadata for key, op in cls._registry.items()}
