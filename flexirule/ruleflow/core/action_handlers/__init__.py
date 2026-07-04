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

	@classmethod
	def get_action_contract(cls):
		"""Return the action type's top-level contract."""
		from flexirule.ruleflow.core.action_handlers.base_contract import ActionContract

		return ActionContract(
			action_type=cls.action_type or "",
			required_fields=[],
			has_next_true=True,
			has_next_false=False,
			terminal=False,
		)

	@classmethod
	def get_operation_contracts(cls) -> dict:
		"""Return operation-level contracts keyed by operation name."""
		return {}

	@classmethod
	def get_runtime_policy(cls, operation: str | None = None, process_operation: dict | None = None) -> dict:
		"""Resolve runtime policy for this handler + optional operation."""
		contract = cls.get_action_contract()
		policy = {
			"allowed_mutations": list(contract.allowed_mutations or []),
			"allowed_return_types": list(contract.allowed_return_types or []),
			"default_return_type": contract.default_return_type,
			"field_labels": dict(contract.field_labels or {}),
			"show_return_type": contract.show_return_type,
			"require_return_type": contract.require_return_type,
			"show_return_variable": contract.show_return_variable,
			"require_return_variable": contract.require_return_variable,
		}

		if operation:
			if contract.operation_policies and operation in contract.operation_policies:
				op_policy = contract.operation_policies[operation]
				for key in ("allowed_mutations", "allowed_return_types"):
					if op_policy.get(key):
						policy[key] = list(op_policy[key])
				if op_policy.get("default_return_type"):
					policy["default_return_type"] = op_policy["default_return_type"]
				if op_policy.get("show_return_type") is not None:
					policy["show_return_type"] = op_policy.get("show_return_type")
				if op_policy.get("require_return_type") is not None:
					policy["require_return_type"] = op_policy.get("require_return_type")
				if op_policy.get("show_return_variable") is not None:
					policy["show_return_variable"] = op_policy.get("show_return_variable")
				if op_policy.get("require_return_variable") is not None:
					policy["require_return_variable"] = op_policy.get("require_return_variable")
				if op_policy.get("field_labels"):
					policy["field_labels"].update(op_policy.get("field_labels", {}))

			# Override with operation contract settings if defined
			op_contracts = cls.get_operation_contracts()
			if operation in op_contracts:
				op_contract = op_contracts[operation]
				for field_def in op_contract.action_overrides:
					fieldname = field_def.get("fieldname")
					if fieldname == "mutation_mode" and field_def.get("options"):
						policy["allowed_mutations"] = field_def["options"]
					elif fieldname == "return_type":
						if field_def.get("options"):
							policy["allowed_return_types"] = field_def["options"]
						if field_def.get("default"):
							policy["default_return_type"] = field_def["default"]
						if "read_only" in field_def:
							policy["show_return_type"] = not field_def.get("read_only", False)
							policy["require_return_type"] = field_def.get("reqd", False)
		return policy

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

	def _build_template_context(self, context, engine=None):
		"""Standard Jinja template context shared by all evaluations."""
		import frappe
		from jinja2 import pass_context

		from flexirule.ruleflow.core.engine import SafeFrappeAPI

		@pass_context
		def format_jinja(jinja_ctx, formatter_type, options=None, val=None):
			if options is None:
				options = {}
			if val is None:
				val = jinja_ctx.get("value")

			if val is None:
				return ""

			formatter_type = str(formatter_type).lower().strip()

			if formatter_type == "uppercase":
				return str(val).upper()
			elif formatter_type == "lowercase":
				return str(val).lower()
			elif formatter_type == "currency":
				symbol = options.get("currency") or ""
				decimals = options.get("decimals")
				if decimals is not None:
					try:
						decimals = int(decimals)
					except (ValueError, TypeError):
						decimals = None
				return frappe.utils.fmt_money(val, precision=decimals, currency=symbol)
			elif formatter_type == "date":
				date_format = options.get("format")
				return frappe.utils.format_date(val, date_format)
			elif formatter_type == "percent":
				try:
					return f"{float(val) * 100:.2f}%"
				except (ValueError, TypeError):
					return f"{val}%"
			elif formatter_type == "number":
				precision = options.get("precision")
				if precision is not None:
					try:
						return f"{float(val):.{int(precision)}f}"
					except (ValueError, TypeError):
						pass
				return str(val)

			return str(val)

		def resolve_helper(first, *args, **kwargs):
			from flexirule.ruleflow.utils.field_resolver import FieldResolver

			if isinstance(first, str):
				resolver_type = first.lower().strip()
				if resolver_type in ("query_record", "query_records"):
					doctype = kwargs.get("doctype")
					fieldname = kwargs.get("fieldname")
					filters = kwargs.get("filters")
					if fieldname:
						return frappe.db.get_value(doctype, filters, fieldname)
					else:
						res = frappe.get_all(doctype, filters=filters, limit=1)
						return res[0] if res else None
				elif resolver_type == "resolve_user":
					return frappe.session.user
				elif resolver_type == "fetch_global_setting":
					return frappe.db.get_single_value(kwargs.get("doctype"), kwargs.get("fieldname"))
				elif resolver_type == "custom":
					method_path = kwargs.get("method")
					if method_path:
						fn = frappe.get_attr(method_path)
						return fn(*args, **kwargs)
					return None

				if context and "doc" in context:
					return FieldResolver.resolve(context.get("doc"), first)
				return None

			if len(args) > 0 and isinstance(args[0], str):
				return FieldResolver.resolve(first, args[0])
			return None

		def normalize_helper(val, steps):
			from flexirule.ruleflow.process.normalization.normalization import apply_transformations

			return apply_transformations(val, steps)

		def condition_helper(compiled_expr_or_payload):
			if not compiled_expr_or_payload:
				return False

			from flexirule.ruleflow.core.compiler import ConditionCompiler

			if isinstance(compiled_expr_or_payload, dict | list):
				compiled_expr = ConditionCompiler().compile(compiled_expr_or_payload)
			else:
				compiled_expr = str(compiled_expr_or_payload)

			if engine and hasattr(engine, "_evaluate_python_condition"):
				return bool(engine._evaluate_python_condition(compiled_expr, context))
			return False

		ctx = {
			"doc": context.get("doc"),
			"vars": context.get("vars", {}),
			"frappe": SafeFrappeAPI(),
			"utils": frappe.utils,
			# Python builtins needed for Jinja templates (Jinja2 does not expose these by default)
			"sum": sum,
			"int": int,
			"str": str,
			"len": len,
			"max": max,
			"min": min,
			"round": round,
			"abs": abs,
			"bool": bool,
			"float": float,
			"format": format_jinja,
			"resolve": resolve_helper,
			"normalize": normalize_helper,
			"condition": condition_helper,
		}
		if engine:
			ctx["rule"] = engine.rule
			ctx["rule_url"] = frappe.utils.get_url_to_form("Rule", engine.rule.name)
		return ctx

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

		doc = context.get("doc")
		if isinstance(doc, dict):
			doc = frappe._dict(doc)
		old_doc = context.get("old_doc")
		if isinstance(old_doc, dict):
			old_doc = frappe._dict(old_doc)

		safe_frappe = context.get("frappe") or frappe
		safe_expression = (expression or "").strip()
		# frappe.safe_eval can block module attribute traversal like frappe.utils.add_days.
		# Normalize common date helpers to direct safe locals.
		safe_expression = safe_expression.replace("frappe.utils.add_days", "add_days")
		safe_expression = safe_expression.replace("frappe.utils.nowdate", "nowdate")
		safe_expression = safe_expression.replace("frappe.utils.getdate", "getdate")
		eval_locals = {
			"doc": doc,
			"old_doc": old_doc,
			"vars": frappe._dict(context.get("vars", {})),
			"context": frappe._dict(context),
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
	_contract_cache: ClassVar[dict | None] = None

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
		cls._contract_cache = None  # Force re-aggregation

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
	def get_action_contract(cls, action_type: str) -> dict:
		"""Get contract for a specific action type."""
		cls._ensure_initialized()
		from flexirule.ruleflow.core.contract_utils import normalize_action_type

		norm_type = normalize_action_type(action_type)
		handler = cls._handlers.get(norm_type)
		if handler:
			return handler.get_action_contract().to_dict()
		return {
			"required_fields": [],
			"has_next_true": True,
			"has_next_false": False,
			"terminal": False,
			"css": {},
			"node_type": "action",
			"category": "Other",
			"configurable": True,
		}

	@classmethod
	def get_all_contracts(cls) -> dict[str, dict]:
		"""Aggregate all action contracts. Cached for performance."""
		cls._ensure_initialized()
		if cls._contract_cache is not None:
			return cls._contract_cache
		cls._contract_cache = {at: h.get_action_contract().to_dict() for at, h in cls._handlers.items()}
		return cls._contract_cache

	@classmethod
	def get_operation_contract(cls, operation: str, process_operation: dict | None = None) -> dict:
		"""Get operation contract from the owning handler."""
		cls._ensure_initialized()
		# Find owning handler for this operation
		for handler in cls._handlers.values():
			op_contracts = handler.get_operation_contracts()
			if operation in op_contracts:
				return op_contracts[operation].to_dict()

		# Fallback to action type based contract:
		from flexirule.ruleflow.core.contract_utils import normalize_action_type

		action_type = None
		for at, handler in cls._handlers.items():
			contract = handler.get_action_contract()
			if operation in (contract.operation_options or []):
				action_type = at
				break
		if not action_type:
			for at in cls._handlers:
				if operation == at:
					action_type = at
					break

		if action_type:
			base_contract = cls.get_action_contract(action_type)
			return {
				"Rule": [],
				"Rule Action": [
					{"fieldname": "action_type", "default": action_type},
					{"fieldname": "operation", "default": operation if operation != action_type else None},
					{
						"fieldname": "description",
						"description": base_contract.get("description", f"Executes {operation}"),
					},
				]
				+ [{"fieldname": f, "reqd": 1} for f in base_contract.get("required_fields", [])],
				"Validation": base_contract.get("validation", {}),
			}

		return {
			"Rule": [],
			"Rule Action": [{"fieldname": "description", "description": f"Unknown operation: {operation}"}],
			"Validation": {},
		}

	@classmethod
	def get_all_operation_contracts(cls) -> dict[str, dict]:
		"""Aggregate all operation contracts from all handlers."""
		cls._ensure_initialized()
		result = {}
		for handler in cls._handlers.values():
			for op_name, oc in handler.get_operation_contracts().items():
				result[op_name] = oc.to_dict()
		return result

	@classmethod
	def get_effective_policy(
		cls, action_type: str | None, operation: str | None = None, process_operation: dict | None = None
	) -> dict:
		"""Resolve action policy including operation-level overrides."""
		cls._ensure_initialized()
		from flexirule.ruleflow.core.contract_utils import normalize_action_type

		norm_type = normalize_action_type(action_type) if action_type else ""
		handler = cls._handlers.get(norm_type)

		policy = {}
		if handler:
			policy = handler.get_runtime_policy(operation, process_operation)

		# Add support for Process Handler-specific dynamic policies
		if norm_type == "Process" and process_operation and operation:
			from flexirule.ruleflow.core.process_contract_v2 import resolve_process_operation_contract_v2

			process_name = process_operation.get("parent") if isinstance(process_operation, dict) else None
			if process_name:
				try:
					contract_v2 = resolve_process_operation_contract_v2(
						process_name,
						operation,
						process_operation,
						strict=True,
					)
					for key, value in (contract_v2.get("policy") or {}).items():
						if value is not None:
							policy[key] = value
				except Exception:
					pass
		elif norm_type == "Process" and process_operation:
			# Import here to avoid circular imports
			from flexirule.ruleflow.core.contracts import infer_process_operation_policy

			dynamic_policy = infer_process_operation_policy(process_operation)
			for key, value in dynamic_policy.items():
				if value is not None:
					policy[key] = value

		return policy

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
			assignment,
			condition,
			document_action,
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
		cls._contract_cache = None
