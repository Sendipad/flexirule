# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

"""
Context Manager for FlexiRule Rule Engine

Provides structured variable storage, return type validation,
and variable availability tracking during rule execution.
"""

from typing import ClassVar

import frappe
from frappe import _


class ContextManager:
	"""
	Manages execution context variables for the rule engine.

	Provides a structured interface around the raw context dict,
	adding type validation, variable tracking, and safe access patterns.
	"""

	# Mapping of return_type strings to Python types
	TYPE_MAP: ClassVar[dict[str, tuple]] = {
		"Yes / No": (bool,),
		"Single Record": (dict,),
		"List of Values": (list, tuple, str, int, float, bool),
		"List of Records": (list,),
		"Full Document": (dict,),
	}

	def __init__(self, context: dict):
		"""
		Initialize with the execution context dict.

		Args:
		    context: The full execution context dict containing 'vars', 'doc', etc.
		"""
		self.context = context
		self._variable_history: list[dict] = []  # Track when variables were set

	@property
	def vars(self) -> dict:
		"""Access the variables sub-dict."""
		return self.context.setdefault("vars", {})

	@property
	def doc(self):
		"""Access the context document."""
		return self.context.get("doc")

	def set_variable(self, name: str, value, return_type: str | None = None):
		"""
		Set a context variable with optional type validation.

		Args:
		    name: Variable name
		    value: Variable value
		    return_type: Optional declared return type for validation

		Raises:
		    frappe.ValidationError: If value doesn't match declared return_type
		"""
		normalized_return_type = self.normalize_return_type(return_type)
		if normalized_return_type and normalized_return_type in self.TYPE_MAP:
			self.validate_return_type(value, normalized_return_type, name)

		self.vars[name] = value
		self._variable_history.append(
			{
				"name": name,
				"type": type(value).__name__,
				"declared_type": normalized_return_type,
			}
		)

	def get_variable(self, name: str, default=None):
		"""
		Get a context variable value.

		Args:
		    name: Variable name
		    default: Default value if variable doesn't exist

		Returns:
		    Variable value or default
		"""
		return self.vars.get(name, default)

	def has_variable(self, name: str) -> bool:
		"""Check if a variable exists in context."""
		return name in self.vars

	def get_available_variables(self) -> list[dict]:
		"""
		Get list of all available variables with their types.

		Returns:
		    List of dicts with 'name', 'type', 'declared_type' keys
		"""
		result = []
		for name, value in self.vars.items():
			# Find declared type from history
			declared_type = None
			for entry in reversed(self._variable_history):
				if entry["name"] == name:
					declared_type = entry.get("declared_type")
					break

			result.append(
				{
					"name": name,
					"type": type(value).__name__,
					"declared_type": declared_type,
					"value_preview": self._preview_value(value),
				}
			)

		return result

	def validate_return_type(self, value, return_type: str | None, var_name: str = "result"):
		"""
		Validate that a value matches the declared return type.

		Args:
		    value: The value to validate
		    return_type: Expected type string
		    var_name: Variable name for error messages
		"""
		return_type = self.normalize_return_type(return_type)
		if not return_type:
			return

		expected_types = self.TYPE_MAP.get(return_type)
		if not expected_types:
			return  # Unknown type, skip validation

		# None is always acceptable
		if value is None:
			return

		if not isinstance(value, expected_types):
			frappe.throw(
				_("Return type mismatch for '{0}': expected {1}, got {2}").format(
					var_name, return_type, type(value).__name__
				)
			)

		# Additional validation for "List of Records"
		if return_type == "List of Records" and isinstance(value, list):
			for i, item in enumerate(value):
				if item is not None and not isinstance(item, dict):
					frappe.throw(
						_("Return type mismatch for '{0}': item at index {1} is {2}, expected dict").format(
							var_name, i, type(item).__name__
						)
					)

	def validate_return_keys(self, value, expected_keys: list[dict], var_name: str = "result"):
		"""
		Validate that a result has the expected schema keys.

		Args:
		    value: The result value (dict or list of dict)
		    expected_keys: List of dicts with 'key' field
		    var_name: Variable name for error messages
		"""
		if not expected_keys or value is None:
			return

		key_names = {
			(k.get("fieldname") or k.get("key"))
			for k in expected_keys
			if (k.get("fieldname") or k.get("key"))
		}
		if not key_names:
			return

		# Get actual keys from value
		actual_keys = set()
		if isinstance(value, dict):
			actual_keys = set(value.keys())
		elif isinstance(value, list) and value and isinstance(value[0], dict):
			actual_keys = set(value[0].keys())

		missing = key_names - actual_keys
		if missing:
			frappe.logger().warning(
				f"Return keys mismatch for '{var_name}': expected keys {missing} not found in result"
			)

	def normalize_return_type(self, return_type: str | None) -> str | None:
		"""Return normalized return type label."""
		return return_type

	def apply_mutation(self, mutation_mode: str, var_name: str, value, context: dict | None = None):
		"""
		Apply a mutation mode to store/update a value.

		Args:
		    mutation_mode: One of the mutation mode options
		    var_name: Target variable/field name
		    value: Value to apply
		    context: Optional explicit context (uses self.context if not provided)
		"""
		ctx = context or self.context

		if mutation_mode == "Set Doc Field":
			doc = ctx.get("doc")
			if doc:
				doc.set(var_name, value)

		elif mutation_mode == "Update Doc Field":
			doc = ctx.get("doc")
			if doc and isinstance(value, dict):
				for k, v in value.items():
					doc.set(k, v)

		elif mutation_mode == "Set Context Variable":
			self.vars[var_name] = value

		elif mutation_mode == "Update Context Variable":
			existing = self.vars.get(var_name, {})
			if isinstance(existing, dict) and isinstance(value, dict):
				existing.update(value)
				self.vars[var_name] = existing
			else:
				self.vars[var_name] = value

		elif mutation_mode == "Append to Context Variable":
			existing = self.vars.get(var_name, [])
			if isinstance(existing, list):
				existing.append(value)
			else:
				self.vars[var_name] = [existing, value]

		elif mutation_mode == "Batch Database Set":
			# Direct database update (bypasses ORM)
			doc = ctx.get("doc")
			if doc and isinstance(value, dict):
				frappe.db.set_value(doc.doctype, doc.name, value, update_modified=True)

	def _preview_value(self, value, max_len=100):
		"""Get a short preview of a value for debugging."""
		preview = repr(value)
		if len(preview) > max_len:
			return preview[:max_len] + "..."
		return preview
