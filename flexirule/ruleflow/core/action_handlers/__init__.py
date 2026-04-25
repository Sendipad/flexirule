# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

"""
Action Handler System using Strategy Pattern.

This module provides a pluggable architecture for action type handlers,
allowing third-party apps to register custom action types without modifying
the core engine.

Usage:
    from flexirule.ruleflow.core.action_handlers import HandlerRegistry, ActionHandler

    class MyCustomHandler(ActionHandler):
        action_type = "My Custom Action"

        def execute(self, action, context, engine):
            # Custom logic here
            return result, next_action_id

    HandlerRegistry.register(MyCustomHandler())
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar, Optional

if TYPE_CHECKING:
	from flexirule.ruleflow.core.engine import RuleEngine


class ActionHandler(ABC):
	"""
	Abstract base class for all action handlers.

	Each handler is responsible for executing a specific action type.
	Handlers are stateless singletons registered with the HandlerRegistry.
	"""

	action_type: str | None = None  # Must be set by subclass

	@abstractmethod
	def execute(self, action, context: dict, engine: "RuleEngine") -> tuple[Any, str | None]:
		"""
		Execute the action.

		Args:
		    action: The Rule Action row (child table row)
		    context: Execution context dict with doc, vars, frappe, etc.
		    engine: Reference to the RuleEngine instance for utility methods

		Returns:
		    Tuple of (result, next_action_id)
		    - result: The execution result (can be any type)
		    - next_action_id: ID of the next action to execute, or None to stop
		"""
		pass

	def validate(self, action, context: dict) -> list:
		"""
		Optional validation before execution.

		Override this method to add pre-execution validation.

		Args:
			action: The Rule Action row
			context: Execution context

		Returns:
			List of error message strings (empty if valid)
		"""
		return []

	def _parse_config(self, config_str):
		"""Safely parse config JSON."""
		if not config_str:
			return {}
		if isinstance(config_str, dict):
			return config_str
		try:
			import json

			return json.loads(config_str)
		except (json.JSONDecodeError, TypeError):
			return {}

	def _resolve_filters(self, filters, context):
		"""
		Resolve template expressions in filter values.
		Supports dict, list of lists, and the new unified list of dicts format.
		"""
		if not filters:
			return filters

		if isinstance(filters, list):
			resolved_list = []
			for item in filters:
				if isinstance(item, dict) and ("field" in item or "fieldname" in item):
					# New unified format detection
					res_row = {k: self._resolve_value_expression(v, context) for k, v in item.items()}
					fname = res_row.get("field") or res_row.get("fieldname")
					fop = res_row.get("operator") or res_row.get("op") or "="
					fval = res_row.get("value")
					fdt = res_row.get("doctype")

					if fdt:
						resolved_list.append([fdt, fname, fop, fval])
					else:
						resolved_list.append([fname, fop, fval])
				elif isinstance(item, list | dict):
					# Recurse for nested structures
					resolved_list.append(self._resolve_filters(item, context))
				else:
					resolved_list.append(self._resolve_value_expression(item, context))
			return resolved_list

		if isinstance(filters, dict):
			resolved = {}
			for key, value in filters.items():
				resolved[key] = self._resolve_value_expression(value, context)
			return resolved

		# Handle individual values
		return self._resolve_value_expression(filters, context)

	def _resolve_value_expression(self, value, context):
		"""Helper to resolve a single value (or list of values) if it contains a template expression."""
		if isinstance(value, list):
			return [self._resolve_value_expression(v, context) for v in value]

		if isinstance(value, str) and "{" in value:
			try:
				# Support multiple expressions in one string or just one wrapped in {}
				if value.startswith("{") and value.endswith("}") and value.count("{") == 1:
					inner_expr = value[1 : len(value) - 1]
					return self._safe_eval(inner_expr, context)

				# Fallback: template-like replacement for embedded {vars}
				import re

				def replace(match):
					expr = match.group(1)
					try:
						return str(self._safe_eval(expr, context))
					except Exception:
						return match.group(0)

				return re.sub(r"{(.*?)}", replace, value)
			except Exception:
				return value
		return value

	def _safe_eval(self, expression, context):
		"""Evaluate expressions using frappe.safe_eval."""
		import frappe
		from frappe.utils import add_days, getdate, nowdate

		safe_frappe = context.get("frappe") or frappe
		safe_expression = (expression or "").strip()
		# frappe.safe_eval can block module attribute traversal like frappe.utils.add_days.
		# Normalize common date helpers to direct safe locals.
		safe_expression = safe_expression.replace("frappe.utils.add_days", "add_days")
		safe_expression = safe_expression.replace("frappe.utils.nowdate", "nowdate")
		safe_expression = safe_expression.replace("frappe.utils.getdate", "getdate")
		eval_locals = {
			"doc": context.get("doc"),
			"old_doc": context.get("old_doc"),
			"vars": context.get("vars", {}),
			"item": context.get("item"),
			"loop": context.get("loop"),
			"add_days": add_days,
			"nowdate": nowdate,
			"getdate": getdate,
			"any": any,
			"all": all,
		}
		return frappe.safe_eval(
			safe_expression,
			eval_globals={"frappe": safe_frappe},
			eval_locals=eval_locals,
		)

	def __repr__(self):
		return f"<{self.__class__.__name__}(action_type='{self.action_type}')>"


class HandlerRegistry:
	"""
	Registry for action handlers.

	This registry allows plugin-based extension of action types.
	Third-party apps can register custom handlers that will be
	automatically picked up by the RuleEngine.
	"""

	_handlers: ClassVar[dict] = {}
	_initialized: bool = False

	@classmethod
	def register(cls, handler: ActionHandler) -> None:
		"""
		Register a handler for its action type.

		Args:
		    handler: An ActionHandler instance

		Raises:
		    ValueError: If handler has no action_type set
		"""
		if not handler.action_type:
			raise ValueError(f"Handler {handler.__class__.__name__} must set 'action_type' class attribute")
		cls._handlers[handler.action_type] = handler

	@classmethod
	def get(cls, action_type: str) -> ActionHandler | None:
		"""
		Get the handler for an action type.

		Args:
		    action_type: The action type string (e.g., "Condition", "Process")

		Returns:
		    The registered handler, or None if not found
		"""
		cls._ensure_initialized()
		return cls._handlers.get(action_type)

	@classmethod
	def all(cls) -> dict:
		"""
		Get all registered handlers.

		Returns:
		    Dict mapping action_type -> handler instance
		"""
		cls._ensure_initialized()
		return cls._handlers.copy()

	@classmethod
	def action_types(cls) -> list:
		"""
		Get list of all registered action types.

		Returns:
		    List of action type strings
		"""
		cls._ensure_initialized()
		return list(cls._handlers.keys())

	@classmethod
	def _ensure_initialized(cls) -> None:
		"""
		Lazily load all built-in handlers on first access.

		This avoids circular imports and ensures handlers are loaded
		when needed.
		"""
		if cls._initialized:
			return

		# Import all built-in handlers to trigger registration
		from flexirule.ruleflow.core.action_handlers import (
			condition,
			create_doc,
			loop,
			process,
			query_records,
			simple_actions,
			sub_rule,
			switch,
		)

		cls._initialized = True

	@classmethod
	def reset(cls) -> None:
		"""
		Reset the registry (for testing purposes).
		"""
		cls._handlers = {}
		cls._initialized = False
