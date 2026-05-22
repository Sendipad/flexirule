# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

import json
from functools import lru_cache
from typing import Any

import frappe
from frappe import _

from flexirule.ruleflow.core.action_handlers import ActionHandler, HandlerRegistry
from flexirule.ruleflow.core.action_plan_cache import get_action_plan
from flexirule.ruleflow.core.context_manager import ContextManager
from flexirule.ruleflow.core.exceptions import MethodExecutionError
from flexirule.ruleflow.core.operators import AssignmentOperatorRegistry
from flexirule.ruleflow.core.process_runtime_v2 import AFTER_EVENT_MUTATION_BLOCKLIST


class AssignmentHandler(ActionHandler):
	"""Handler for Assignment action type - batch state mutation."""

	action_type = "Assignment"

	def execute(self, action, context, engine):
		"""
		Execute Assignment action - sequential batch mutations.

		Parses config JSON array of assignment objects:
		[
		    {
		        "target": "doc.status",
		        "operator": "set",
		        "value": "Closed"
		    }
		]
		"""
		plan = get_action_plan(engine.rule, action)
		assignments = plan.get("rows")
		if not isinstance(assignments, list):
			config_key = self._to_config_cache_key(getattr(action, "config", "[]") or "[]")
			try:
				assignments = list(self._get_compiled_plan(config_key))
			except Exception:
				engine._log("ERROR", _("Assignment action config is not valid JSON"))
				raise MethodExecutionError(_("Assignment action config is not valid JSON array"))

		event_name = context.get("event_name")

		for idx, assignment in enumerate(assignments):
			target_path = assignment.get("target")
			operator_key = assignment.get("operator", "set")
			when_expression = assignment.get("when_expression") or ""

			if not target_path:
				engine._log("WARNING", _("Assignment index {0} missing target path, skipping").format(idx))
				continue

			# 1. System path protection
			self._validate_target_path(target_path)

			# 2. Event restriction check
			self._validate_event_restrictions(target_path, event_name)

			# 2.5 Optional row-level execution guard
			if when_expression and not engine._evaluate_python_condition(when_expression, context):
				continue

			# 3. Get operator
			operator = AssignmentOperatorRegistry.get(operator_key)

			# Fetch current value for apply
			current_value = self._get_current_value(target_path, context)

			# 4. Evaluate value if required
			operand_value = None
			if operator.metadata.get("requires_value"):
				# Inject current value so the format/normalization helper can access it
				context_copy = dict(context)
				context_copy["value"] = current_value

				# Compile and resolve using the unified ValueResolver!
				from flexirule.ruleflow.core.value_resolver import get_compiled_resolver

				resolver = get_compiled_resolver(action, f"assign_{idx}", assignment.get("value"))
				operand_value = resolver.resolve(context_copy)

			# 6. Optional: Validate Target Type (deferred for runtime, but operator can check if needed)
			# (In a real implementation, we'd fetch the Frappe metadata for doc.* fields here)
			# operator.validate(target_type, operand_value)

			# 7. Apply operation
			new_value = operator.apply(current_value, operand_value, context)

			# 8. Commit to context via ContextManager or directly
			self._set_value(target_path, new_value, context, engine)

		return None, getattr(action, "next_step_if_true", None)

	def _to_config_cache_key(self, config) -> str:
		if isinstance(config, str):
			return config
		try:
			return json.dumps(config)
		except Exception:
			return "[]"

	@staticmethod
	@lru_cache(maxsize=1024)
	def _get_compiled_plan(config_key: str) -> tuple[dict[str, Any], ...]:
		try:
			rows = json.loads(config_key or "[]")
		except Exception:
			rows = []
		if not isinstance(rows, list):
			rows = []

		compiled_rows: list[dict[str, Any]] = []
		for row in rows:
			if not isinstance(row, dict):
				continue
			compiled = dict(row)
			# Canonicalize operand payload for unified runtime evaluation
			# (legacy rows may store structured payload under value_template_ui/value_template_json).
			if compiled.get("value") is None:
				if compiled.get("value_template_ui") is not None:
					compiled["value"] = compiled.get("value_template_ui")
				elif compiled.get("value_template_json") is not None:
					compiled["value"] = compiled.get("value_template_json")
				elif compiled.get("value_template") is not None:
					compiled["value"] = compiled.get("value_template")
			compiled["when_expression"] = AssignmentHandler._compile_when_expression(compiled)
			compiled_rows.append(compiled)

		return tuple(compiled_rows)

	@classmethod
	def _compile_when_expression(cls, row: dict) -> str:
		python_expr = row.get("pythonExpression")
		if python_expr:
			return python_expr

		when_expression = (row.get("when_expression") or row.get("when") or "").strip()
		if when_expression:
			return when_expression

		when_condition = row.get("when_condition")
		if isinstance(when_condition, dict | list):
			try:
				from flexirule.ruleflow.core.compiler import ConditionCompiler

				return ConditionCompiler().compile(when_condition) or ""
			except Exception:
				return ""

		return ""

	@staticmethod
	def _compile_structured_value_to_jinja(val: dict) -> str:
		"""
		Backward-compatible helper for rule.py metadata compilation (save path).
		Converts a structured value object into an equivalent Jinja template string
		for legacy persistence in the AssignmentOperandSpec fields.
		"""
		if not val:
			return ""

		mode = val.get("mode")

		if mode in {"static", "link", "dynamic_link"}:
			return str(val.get("value") if val.get("value") is not None else "")

		if mode == "variable":
			path = val.get("path")
			if path:
				if not (path.startswith("doc.") or path.startswith("vars.")):
					path = f"vars.{path}"
				return f"{{{{ {path} }}}}"
			return ""

		if mode == "formula":
			expr = val.get("expression") or ""
			return f"{{{{ {expr} }}}}"

		if mode == "formatter" or (mode == "resolver" and val.get("config", {}).get("kind") == "format"):
			config = val.get("config") or {}
			formatter = val.get("formatter") or config.get("fmt_op") or ""
			options = val.get("options") or config or {}
			return f'{{{{ format("{formatter}", {json.dumps(options)}) }}}}'

		if mode == "normalize" or (
			mode == "resolver" and val.get("config", {}).get("kind") == "normalization"
		):
			config = val.get("config") or {}
			steps = val.get("steps") or ([config.get("norm_op")] if config.get("norm_op") else [])
			return f"{{{{ normalize(value, {json.dumps(steps)}) }}}}"

		if mode == "resolver":
			config = val.get("config") or {}
			kind = config.get("kind")

			# Known built-in resolvers → direct Jinja helper call
			if kind:
				expr = val.get("expression") or val.get("value")
				if expr:
					if expr.startswith("{") and expr.endswith("}"):
						return f"{{{{ {expr[1:-1]} }}}}"
					return f"{{{{ {expr} }}}}"

				resolver = val.get("resolver") or val.get("value") or ""
				args = ", ".join(f"{k}={json.dumps(v)}" for k, v in config.items())
				return f'{{{{ resolve("{resolver}", {args}) }}}}'

		if mode == "condition":
			condition = val.get("condition") or {}
			return f"{{{{ condition({json.dumps(condition)}) }}}}"

		return ""

		return ""

	def _validate_target_path(self, target_path: str):
		"""Prevent mutation of system paths."""
		forbidden_prefixes = ("meta.", "frappe.", "rule.", "caller.")
		if target_path.startswith(forbidden_prefixes):
			raise MethodExecutionError(_("Cannot mutate protected system path '{0}'").format(target_path))
		if not (target_path.startswith("doc.") or target_path.startswith("vars.")):
			raise MethodExecutionError(
				_("Assignment target '{0}' must start with 'doc.' or 'vars.'").format(target_path)
			)

	def _validate_event_restrictions(self, target_path: str, event_name: str | None):
		"""Prevent doc.* mutations in after-save events."""
		if not event_name or not target_path.startswith("doc."):
			return

		if event_name in AFTER_EVENT_MUTATION_BLOCKLIST:
			raise MethodExecutionError(
				_("Cannot mutate document field '{0}' during event '{1}'").format(target_path, event_name)
			)

	def _get_current_value(self, target_path: str, context: dict):
		"""Retrieve the current value at the target path."""
		parts = target_path.split(".")
		base = parts[0]

		if base == "doc":
			current = context.get("doc")
		elif base == "vars":
			current = context.get("vars", {})
		else:
			return None

		if not current:
			return None

		for part in parts[1:]:
			if isinstance(current, dict):
				current = current.get(part)
			elif hasattr(current, "get"):
				current = current.get(part)
			else:
				return None

			if current is None:
				return None

		return current

	def _set_value(self, target_path: str, value, context: dict, engine):
		"""Set the new value at the target path."""
		parts = target_path.split(".")
		base = parts[0]

		if base == "doc":
			doc = context.get("doc")
			if doc:
				if hasattr(doc, "set") and callable(getattr(doc, "set", None)):
					# Support dot notation setting on doc if it's a child table?
					# For v1, limit to root doc fields.
					if len(parts) == 2:
						doc.set(parts[1], value)
						engine._log("INFO", _("Assignment: Set doc.{0} = {1}").format(parts[1], value))
					else:
						raise MethodExecutionError(
							_("Deep document path assignment is not yet supported in v1")
						)
				elif isinstance(doc, dict):
					if len(parts) == 2:
						doc[parts[1]] = value
						engine._log("INFO", _("Assignment: Set doc.{0} = {1}").format(parts[1], value))
					else:
						raise MethodExecutionError(
							_("Deep document path assignment is not yet supported in v1")
						)

		elif base == "vars":
			if "vars" not in context:
				context["vars"] = {}

			current = context["vars"]
			# Create intermediate dicts if they don't exist
			for part in parts[1:-1]:
				if part not in current or not isinstance(current[part], dict):
					current[part] = {}
				current = current[part]

			current[parts[-1]] = value
			engine._log("INFO", _("Assignment: Set {0} = {1}").format(target_path, value))


# Register the handler
HandlerRegistry.register(AssignmentHandler())
