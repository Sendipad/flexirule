# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _

from flexirule.ruleflow.core.action_handlers import ActionHandler, HandlerRegistry
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
		config_str = getattr(action, "config", "[]") or "[]"
		try:
			assignments = json.loads(config_str)
			if not isinstance(assignments, list):
				assignments = []
		except Exception:
			engine._log("ERROR", _("Assignment action config is not valid JSON"))
			raise MethodExecutionError(_("Assignment action config is not valid JSON array"))

		event_name = context.get("event_name")

		# Build shared Jinja template context for value evaluation
		template_context = self._build_template_context(context, engine)

		for idx, assignment in enumerate(assignments):
			target_path = assignment.get("target")
			operator_key = assignment.get("operator", "set")

			# Canonical key: value_template (Jinja string compiled by the frontend).
			# Fallback: value (legacy key used before FSVC unification).
			# NOTE: value_template_ui is the raw AST saved by the frontend for
			# re-editing purposes only — the backend must never read it.
			value_template = assignment.get("value_template") or assignment.get("value")

			if not target_path:
				engine._log("WARNING", _("Assignment index {0} missing target path, skipping").format(idx))
				continue

			# 1. System path protection
			self._validate_target_path(target_path)

			# 2. Event restriction check
			self._validate_event_restrictions(target_path, event_name)

			# 3. Get operator
			operator = AssignmentOperatorRegistry.get(operator_key)

			# 4. Evaluate value if required
			operand_value = None
			if operator.metadata.get("requires_value"):
				if isinstance(value_template, str) and ("{{" in value_template or "{%" in value_template):
					# Render Jinja template
					# nosemgrep: frappe-semgrep-rules.rules.security.frappe-ssti
					operand_value = frappe.render_template(
						value_template, template_context
					)  # nosemgrep: frappe-ssti
				else:
					operand_value = value_template

			# 5. Fetch current value for apply
			current_value = self._get_current_value(target_path, context)

			# 6. Optional: Validate Target Type (deferred for runtime, but operator can check if needed)
			# (In a real implementation, we'd fetch the Frappe metadata for doc.* fields here)
			# operator.validate(target_type, operand_value)

			# 7. Apply operation
			new_value = operator.apply(current_value, operand_value, context)

			# 8. Commit to context via ContextManager or directly
			self._set_value(target_path, new_value, context, engine)

		return None, getattr(action, "next_step_if_true", None)

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
			if doc and hasattr(doc, "set"):
				# Support dot notation setting on doc if it's a child table?
				# For v1, limit to root doc fields.
				if len(parts) == 2:
					doc.set(parts[1], value)
					engine._log("INFO", _("Assignment: Set doc.{0} = {1}").format(parts[1], value))
				else:
					raise MethodExecutionError(_("Deep document path assignment is not yet supported in v1"))

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
