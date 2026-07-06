# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

"""
Sub-Rule Action Handler.

Executes another Rule as a nested sub-rule with proper context isolation
and cycle detection.
"""

import json
import re

import frappe
from frappe import _

from flexirule.ruleflow.core.action_handlers import ActionHandler, HandlerRegistry
from flexirule.ruleflow.core.action_handlers.base_contract import ActionContract, OperationContract
from flexirule.ruleflow.core.exceptions import CycleDetectedError, MethodExecutionError
from flexirule.ruleflow.core.permissions import can_skip_permissions
from flexirule.ruleflow.utils.mapping import apply_input_mapping, apply_output_mapping

# Maximum nesting depth for sub-rule calls
MAX_SUB_RULE_DEPTH = 2


class SubRuleVarsOverlay(dict):
	"""
	Copy-on-write overlay for sub-rule context vars.

	- Reads fall back to parent vars.
	- Writes stay local to sub-rule execution.
	- Mutable parent values are shallow-copied on first access to avoid
	  mutating parent context state.
	"""

	def __init__(self, parent_vars=None):
		super().__init__()
		self._parent = parent_vars or {}

	def __contains__(self, key):
		return dict.__contains__(self, key) or key in self._parent

	def __getitem__(self, key):
		if dict.__contains__(self, key):
			return dict.__getitem__(self, key)
		if key not in self._parent:
			raise KeyError(key)
		return self._promote_parent_value(key)

	def get(self, key, default=None):
		if dict.__contains__(self, key):
			return dict.__getitem__(self, key)
		if key not in self._parent:
			return default
		return self._promote_parent_value(key)

	def setdefault(self, key, default=None):
		if key in self:
			return self.get(key)
		dict.__setitem__(self, key, default)
		return default

	def export_mutations(self):
		"""Return only vars written by the sub-rule."""
		return dict(self)

	def _promote_parent_value(self, key):
		value = self._parent.get(key)
		if isinstance(value, dict):
			local_dict = value.copy()
			dict.__setitem__(self, key, local_dict)
			return local_dict
		if isinstance(value, list):
			local_list = list(value)
			dict.__setitem__(self, key, local_list)
			return local_list
		if isinstance(value, set):
			local_set = set(value)
			dict.__setitem__(self, key, local_set)
			return local_set
		return value


class SubRuleHandler(ActionHandler):
	"""Handler for Sub-Rule action type."""

	action_type = "Sub-Rule"

	@classmethod
	def get_action_contract(cls):
		return ActionContract(
			action_type="Sub-Rule",
			required_fields=["rule"],
			has_next_true=True,
			has_next_false=False,
			terminal=False,
			css={"icon": "fa fa-cube", "color": "#ec4899"},
			field_labels={
				"rule": "Sub-Rule Name",
				"skip_conditions": "Skip Compatibility Check",
				"return_type": "Sub-Rule Result Type",
			},
			allowed_mutations=[
				"Set Context Variable",
				"Update Context Variable",
				"Append to Context Variable",
			],
			allowed_return_types=[
				"Single Record",
				"List of Records",
			],
			default_return_type="Single Record",
			show_return_type=True,
			require_return_type=False,
			node_type="sub-rule",
			category="Control Flow",
			configurable=True,
			config_component="SubRuleConfig",
		)

	@classmethod
	def get_operation_contracts(cls) -> dict:
		return {
			"Sub-Rule": OperationContract(
				operation="Sub-Rule",
				action_overrides=[
					{"fieldname": "action_type", "default": "Sub-Rule"},
					{
						"fieldname": "rule",
						"reqd": 1,
						"options": "Rule",
						"link_filters": '[["Rule","trigger_type","=","Callable Event"],["Rule","exposed_as_subrule","=",1]]',
					},
					{
						"fieldname": "skip_conditions",
						"default": 1,
						"description": "⚠️ Bypasses sub-rule's trigger conditions",
					},
					{
						"fieldname": "skip_permissions",
						"read_only_depends_on": "eval:!frappe.user.has_role('System Manager')",
						"description": "⚠️ Requires audit reason when enabled",
					},
					{
						"fieldname": "permission_audit_reason",
						"mandatory_depends_on": "skip_permissions",
						"hidden": "eval:!doc.skip_permissions",
					},
					{"fieldname": "description", "description": "Executes another rule as a subroutine"},
				],
				validation={"backend": "validate_sub_rule"},
			)
		}

	def execute(self, action, context, engine):
		"""
		Execute a Sub-Rule with proper isolation and cycle detection.

		Features:
		- Cross-rule cycle detection via execution_stack
		- Depth limiting (MAX_SUB_RULE_DEPTH)
		- Optional bypass of sub-rule trigger conditions
		- Optional bypass of permission checks
		- Namespaced sub-rule outputs (no implicit parent var merge)

		Returns:
		    Tuple of (None, next_action_id)
		"""
		try:
			action_config = engine._get_action_config(action)

			# Determine Sub Rule name
			sub_rule_name = getattr(action, "rule", None)
			if not sub_rule_name:
				sub_rule_name = action_config.get("sub_rule_name") or action_config.get("rule")

			if not sub_rule_name:
				engine._log("WARNING", _("Sub-Rule action missing rule reference"))
				return None, getattr(action, "next_step_if_true", None)

			# Resolve active version of the logical name
			from flexirule.ruleflow.core.coordinator import RuleCoordinator
			from flexirule.ruleflow.core.rule_service import resolve_rule_reference

			registry = RuleCoordinator.get_runtime_registry()
			resolved_name = registry.get("active_sub_rules", {}).get(sub_rule_name)

			if not resolved_name:
				resolved_name = resolve_rule_reference(
					sub_rule_name,
					active_only=True,
					callable_only=True,
					exposed_only=True,
				)

			if not resolved_name:
				raise MethodExecutionError(_("Sub-Rule {0} not found or is not active").format(sub_rule_name))

			sub_rule_doc = frappe.get_cached_doc("Rule", resolved_name)

			if sub_rule_doc.trigger_type != "Callable Event":
				raise MethodExecutionError(
					_("Sub-Rule {0} must be a Callable Event rule").format(sub_rule_name)
				)

			if not sub_rule_doc.is_exposed_as_subrule():
				raise MethodExecutionError(
					_("Sub-Rule {0} is not exposed for sub-rule execution").format(sub_rule_name)
				)

			if not sub_rule_doc.is_active:
				raise MethodExecutionError(_("Sub-Rule {0} is not active").format(sub_rule_name))

			# Cross-rule cycle detection using logical base name
			caller_base_name = getattr(engine.rule, "base_rule_name", None) or re.sub(
				r"_[vV]\d+$", "", engine.rule.name
			)
			target_base_name = getattr(sub_rule_doc, "base_rule_name", None) or re.sub(
				r"_[vV]\d+$", "", sub_rule_doc.name
			)
			execution_stack = context.get("meta", {}).get("execution_stack", [])
			if target_base_name in execution_stack or caller_base_name == target_base_name:
				cycle_path = " → ".join([*execution_stack, caller_base_name, target_base_name])
				raise CycleDetectedError(_("Cross-rule cycle detected: {0}").format(cycle_path))

			# Determine bypass flags
			skip_conditions = self._get_skip_conditions(action)
			skip_permissions = int(can_skip_permissions(action, context, throw=True))

			engine._log(
				"INFO",
				_("Sub-Rule {0}: skip_conditions={1}, skip_permissions={2}").format(
					sub_rule_name, skip_conditions, skip_permissions
				),
			)

			# Evaluate trigger condition if not skipped
			sub_rule_condition = sub_rule_doc.get_entry_condition()
			if not skip_conditions and sub_rule_condition:
				if not sub_rule_doc.compiled_expression:
					from flexirule.ruleflow.core.compiler import ConditionCompiler

					sub_rule_doc.compiled_expression = ConditionCompiler().compile(
						sub_rule_condition
					)

				caller_rule_meta = {
					"name": engine.rule.name,
					"trigger_type": engine.rule.trigger_type,
					"trigger_event": context.get("event_name") or engine.rule.trigger_event,
					"document_type": engine.rule.document_type,
				}
				target_rule_meta = {
					"name": sub_rule_doc.name,
					"trigger_type": sub_rule_doc.trigger_type,
					"trigger_event": sub_rule_doc.trigger_event,
					"document_type": sub_rule_doc.document_type,
				}
				eligibility_vars = dict(context.get("vars", {}) or {})
				caller_doc = context.get("doc")
				eligibility_vars.update(
					{
						"_caller_rule": engine.rule.name,
						"_caller_trigger_type": engine.rule.trigger_type,
						"_caller_trigger_event": context.get("event_name") or engine.rule.trigger_event,
						"_caller_document_type": engine.rule.document_type,
						"_caller_doc_type": getattr(caller_doc, "doctype", None),
					}
				)

				eligibility_context = dict(context)
				eligibility_context["vars"] = eligibility_vars
				eligibility_context["caller"] = caller_rule_meta
				eligibility_context["rule"] = target_rule_meta
				eligibility_context["doctype"] = (
					engine.rule.document_type
					or getattr(caller_doc, "doctype", None)
					or sub_rule_doc.document_type
				)
				is_eligible = engine._evaluate_python_condition(
					sub_rule_doc.compiled_expression, eligibility_context
				)
				if not is_eligible:
					engine._log(
						"INFO",
						_("Sub-Rule {0}: Trigger condition failed. Skipping execution.").format(
							sub_rule_name
						),
					)
					return None, getattr(action, "next_step_if_true", None)

			# Log permission bypass for audit
			if skip_permissions:
				engine._log(
					"AUDIT",
					_("Sub-Rule {0}: Executing with skip_permissions=True by user {1}").format(
						sub_rule_name, frappe.session.user
					),
				)

			engine._log("INFO", _("BEGIN Sub-Rule: {0}").format(sub_rule_name))

			# Prepare sub-context with isolation:
			# - vars use overlay (no deep-copy, copy-on-write)
			# - meta gets a shallow copy
			sub_context = context.copy()
			sub_context["vars"] = SubRuleVarsOverlay(context.get("vars", {}))
			sub_context["meta"] = context.get("meta", {}).copy()
			sub_context["meta"]["parent_rule"] = engine.rule.name
			caller_base_name = getattr(engine.rule, "base_rule_name", None) or re.sub(
				r"_[vV]\d+$", "", engine.rule.name
			)
			sub_context["meta"]["execution_stack"] = [*execution_stack, caller_base_name]

			# Check depth limit
			current_depth = sub_context["meta"].get("call_depth", 0)
			if current_depth >= MAX_SUB_RULE_DEPTH:
				raise CycleDetectedError(
					_("Max sub-rule recursion depth ({0}) exceeded in {1}").format(
						MAX_SUB_RULE_DEPTH, sub_rule_name
					)
				)
			sub_context["meta"]["call_depth"] = current_depth + 1
			sub_context["meta"]["skip_conditions"] = skip_conditions
			sub_context["meta"]["skip_permissions"] = skip_permissions
			sub_context["meta"]["caller_rule"] = engine.rule.name
			sub_context["meta"]["caller_trigger_type"] = engine.rule.trigger_type
			sub_context["meta"]["caller_trigger_event"] = (
				context.get("event_name") or engine.rule.trigger_event
			)

			# Map parent context values into child vars (reusable mapping semantics)
			input_mapping_json = self._mapping_to_json(action_config.get("input_mapping"))
			if input_mapping_json:
				mapped_inputs = apply_input_mapping(context, input_mapping_json, {})
				for key, value in mapped_inputs.items():
					sub_context["vars"][key] = value

			# Execute sub-rule
			# Import here to avoid circular import
			from flexirule.ruleflow.core.engine import RuleEngine

			sub_engine = RuleEngine(sub_rule_doc, execution_context=sub_context)
			result_context = sub_engine.execute(
				context.get("doc"),
				vars=sub_context["vars"],
				meta=sub_context["meta"],
			)

			sub_result_vars = result_context.get("vars", {})
			if isinstance(sub_result_vars, SubRuleVarsOverlay):
				sub_result_vars = sub_result_vars.export_mutations()
			elif isinstance(sub_result_vars, dict):
				sub_result_vars = dict(sub_result_vars)
			else:
				sub_result_vars = {}

			return_var = (getattr(action, "return_variable", None) or "").strip()
			output_mapping_json = self._mapping_to_json(action_config.get("output_mapping"))

			# No implicit parent merge. Either explicit mapping or deterministic namespace.
			if output_mapping_json:
				apply_output_mapping(sub_result_vars, output_mapping_json, context)
				if return_var:
					context.setdefault("vars", {})[return_var] = sub_result_vars
			else:
				namespace_key = return_var or self._auto_namespace_key(action, sub_rule_name)
				context.setdefault("vars", {})[namespace_key] = sub_result_vars
				if not return_var:
					engine._log(
						"INFO",
						_("Sub-Rule {0}: return_variable not set, output stored in '{1}'").format(
							sub_rule_name, namespace_key
						),
					)
			engine._log("INFO", _("END Sub-Rule: {0}").format(sub_rule_name))

			return None, getattr(action, "next_step_if_true", None)

		except Exception as e:
			engine._log("ERROR", _("Sub-Rule execution failed: {0}").format(str(e)))
			raise

	def _get_skip_conditions(self, action):
		"""Get skip_conditions value from action or config."""
		if hasattr(action, "skip_conditions"):
			return int(action.skip_conditions)

		if getattr(action, "config", None):
			try:
				cfg = json.loads(action.config)
				return int(cfg.get("skip_conditions", 1))
			except Exception:
				pass

		return 1  # Default: skip conditions

	def _auto_namespace_key(self, action, sub_rule_name: str) -> str:
		"""Build deterministic namespace key when return_variable is not provided."""
		action_id = getattr(action, "action_id", None) or sub_rule_name or "subrule"
		safe_action_id = "".join(ch if (ch.isalnum() or ch == "_") else "_" for ch in str(action_id))
		return f"subrule_{safe_action_id}"

	def _mapping_to_json(self, value) -> str | None:
		"""Normalize mapping payload to JSON string for mapping utils."""
		if not value:
			return None
		if isinstance(value, str):
			return value
		if isinstance(value, dict):
			return json.dumps(value)
		if isinstance(value, list):
			normalized = {}
			for row in value:
				if not isinstance(row, dict):
					continue
				source = row.get("source") or row.get("source_expression")
				target = row.get("target")
				if source and target:
					normalized[target] = source
			return json.dumps(normalized) if normalized else None
		return None


# Register the handler
HandlerRegistry.register(SubRuleHandler())
