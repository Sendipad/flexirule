# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

"""
Central rule validation service.

Provides structured validation results that can be reused from
backend form save and frontend builder prechecks.

Validation Modes:
  - 'full':  Complete validation (activation). Graph integrity, single
             entry node, trigger alignment all enforced.
  - 'draft': Relaxed validation (building). Skips activation-only checks.
             Allows unreachable nodes, incomplete graphs.
  - 'node':  Single-action validation. Validates one action in isolation
             against its contract + handler. Used by config modal "save".
"""

from __future__ import annotations

import json
from collections.abc import Mapping

import frappe
from frappe import _
from jsonschema import ValidationError as JsonSchemaValidationError
from jsonschema import validate as jsonschema_validate

from flexirule.ruleflow.core.action_handlers import HandlerRegistry
from flexirule.ruleflow.core.condition_payload import get_condition_payload
from flexirule.ruleflow.core.contracts import (
	get_contract,
	get_effective_action_policy,
	get_required_fields,
	get_trigger_type_contract,
	is_release_disabled_action,
	normalize_action_type,
)
from flexirule.ruleflow.core.process_contract_v2 import resolve_process_operation_contract_v2
from flexirule.ruleflow.utils.graph_validator import validate_graph_integrity

# Valid validation modes
VALIDATION_MODES = {"full", "draft", "node"}


def validate_rule_definition(rule_doc, mode="full") -> dict:
	"""Validate rule payload/doc and return structured errors/warnings.

	Args:
	    rule_doc: Rule document (Frappe doc or dict payload)
	    mode: Validation mode — 'full' | 'draft' | 'node'
	        - 'full':  Complete validation for activation
	        - 'draft': Relaxed validation for building (skips activation checks)
	        - 'node':  Single-action validation (requires action_id in rule_doc)
	"""
	if mode not in VALIDATION_MODES:
		mode = "full"

	rule = _coerce_rule_doc(rule_doc)
	errors: list[str] = []
	warnings: list[str] = []

	# Node mode: validate a single action in isolation
	if mode == "node":
		return _validate_single_action(rule, rule_doc, errors, warnings)

	_normalize_hidden_trigger_fields(rule)
	if mode == "full":
		_validate_trigger_requirements(rule, errors)

	actions = list(_safe_get(rule, "actions", []) or [])
	operation_metadata = _build_operation_metadata(actions)

	for action in actions:
		action_label = _safe_get(action, "action_label") or _safe_get(action, "action_id") or _("(unnamed)")
		action_type_raw = _safe_get(action, "action_type")
		action_type = normalize_action_type(action_type_raw)

		_validate_action_json(action, action_label, errors)

		if _is_empty(action_type):
			errors.append(_("Action '{0}' has no action_type").format(action_label))
			continue

		if action_type == "Stop" and _is_empty(_safe_get(action, "operation")):
			_safe_set(action, "operation", "Success")

		if is_release_disabled_action(action_type):
			errors.append(_("Action '{0}' uses disabled type '{1}'").format(action_label, action_type))

		_validate_action_contracts(
			action,
			action_type,
			action_label,
			operation_metadata,
			errors,
			mode=mode,
		)
		_validate_action_specifics(rule, action, action_type, action_label, warnings, errors)

		handler = HandlerRegistry.get(action_type)
		if handler:
			handler_errors = handler.validate(action, {"doc": None, "vars": {}}) or []
			for err in handler_errors:
				errors.append(
					_("Action '{0}' ({1}) validation failed: {2}").format(action_label, action_type, err)
				)

	dependency_result = _validate_variable_dependencies(actions, operation_metadata)
	errors.extend(dependency_result["errors"])
	warnings.extend(dependency_result["warnings"])

	flow_result = _validate_flow_constraints(rule, actions, operation_metadata)
	errors.extend(flow_result["errors"])
	warnings.extend(flow_result["warnings"])

	if hasattr(rule, "validate_no_sub_rule_cycles"):
		_capture_validation(errors, rule.validate_no_sub_rule_cycles)
	if hasattr(rule, "validate_variable_availability"):
		_capture_validation(errors, rule.validate_variable_availability)

	# Activation-only checks: skip in 'draft' mode
	is_active = _is_truthy(_safe_get(rule, "is_active"))
	if mode == "full" or is_active:
		_capture_validation(errors, validate_graph_integrity, rule)

		entry_nodes = [
			action
			for action in actions
			if _safe_get(action, "action_type") == "Entry Action" or _safe_get(action, "action_id") == "root"
		]
		if len(entry_nodes) != 1:
			errors.append(_("Active Rule must have exactly one Entry Action (Start) node."))

		if hasattr(rule, "validate_trigger_alignment"):
			_capture_validation(errors, rule.validate_trigger_alignment)

	return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings, "mode": mode}


def validate_single_action(rule_name, action_id) -> dict:
	"""Validate a single action within a rule in isolation.

	Useful for the frontend config modal to validate on "Save" without
	running full rule validation.

	Args:
	    rule_name: Rule document name
	    action_id: The action_id to validate

	Returns:
	    dict: {"valid": bool, "errors": [], "warnings": []}
	"""
	try:
		rule = frappe.get_doc("Rule", rule_name)
	except frappe.DoesNotExistError:
		return {"valid": False, "errors": [_("Rule not found: {0}").format(rule_name)], "warnings": []}

	action = None
	for a in rule.actions or []:
		if _safe_get(a, "action_id") == action_id:
			action = a
			break

	if not action:
		return {"valid": False, "errors": [_("Action not found: {0}").format(action_id)], "warnings": []}

	errors: list[str] = []
	warnings: list[str] = []
	return _validate_single_action(rule, action, errors, warnings)


def _validate_single_action(rule, action, errors, warnings) -> dict:
	"""Internal: validate one action against contracts + handlers."""
	action_label = _safe_get(action, "action_label") or _safe_get(action, "action_id") or _("(unnamed)")
	action_type_raw = _safe_get(action, "action_type")
	action_type = normalize_action_type(action_type_raw)

	if _is_empty(action_type):
		errors.append(_("Action '{0}' has no action_type").format(action_label))
		return {"valid": False, "errors": errors, "warnings": warnings, "mode": "node"}

	_validate_action_json(action, action_label, errors)

	if action_type == "Stop" and _is_empty(_safe_get(action, "operation")):
		_safe_set(action, "operation", "Success")

	if is_release_disabled_action(action_type):
		errors.append(_("Action '{0}' uses disabled type '{1}'").format(action_label, action_type))

	actions = list(_safe_get(rule, "actions", []) or [])
	operation_metadata = _build_operation_metadata(actions)

	_validate_action_contracts(action, action_type, action_label, operation_metadata, errors, mode="node")
	_validate_action_specifics(rule, action, action_type, action_label, warnings, errors)

	handler = HandlerRegistry.get(action_type)
	if handler:
		handler_errors = handler.validate(action, {"doc": None, "vars": {}}) or []
		for err in handler_errors:
			errors.append(
				_("Action '{0}' ({1}) validation failed: {2}").format(action_label, action_type, err)
			)

	return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings, "mode": "node"}


def _coerce_rule_doc(rule_doc):
	if hasattr(rule_doc, "doctype"):
		return rule_doc

	payload = dict(rule_doc or {})
	payload.setdefault("doctype", "Rule")
	return frappe.get_doc(payload)


def _validate_trigger_requirements(rule_doc, errors: list[str]) -> None:
	trigger_type = _safe_get(rule_doc, "trigger_type")
	trigger_contract = get_trigger_type_contract(trigger_type)

	for fieldname in trigger_contract.get("required_fields", []):
		if _is_empty(_safe_get(rule_doc, fieldname)):
			errors.append(_("Missing required trigger field: {0}").format(fieldname))


def _normalize_hidden_trigger_fields(rule_doc) -> None:
	trigger_type = _safe_get(rule_doc, "trigger_type")
	trigger_contract = get_trigger_type_contract(trigger_type)

	for fieldname in trigger_contract.get("hidden_fields", []):
		if not _is_empty(_safe_get(rule_doc, fieldname)):
			_safe_set(rule_doc, fieldname, None)


def _validate_action_json(action, action_label: str, errors: list[str]) -> None:
	config = _safe_get(action, "config")
	config_data = _validate_json_value(config, _("Action {0}: Configuration").format(action_label), errors)

	if not isinstance(config_data, Mapping):
		return

	input_mapping = config_data.get("input_mapping")
	if isinstance(input_mapping, str):
		_validate_json_value(input_mapping, _("Action {0}: Input Mapping").format(action_label), errors)

	output_mapping = config_data.get("output_mapping")
	if isinstance(output_mapping, str):
		_validate_json_value(output_mapping, _("Action {0}: Output Mapping").format(action_label), errors)


def _validate_action_contracts(
	action,
	action_type: str,
	action_label: str,
	operation_metadata: dict | None,
	errors: list[str],
	mode: str = "full",
) -> None:
	contract = get_contract(action_type)
	operation = _safe_get(action, "operation")
	operation_metadata = operation_metadata or {}
	return_type = None
	process_operation = None
	if action_type == "Process" and _safe_get(action, "process_name") and operation:
		process_operation = operation_metadata.get(f"{_safe_get(action, 'process_name')}:{operation}")
	effective_policy = get_effective_action_policy(
		action_type,
		operation=operation,
		process_operation=process_operation,
	)
	if action_type == "Process" and process_operation and operation and _safe_get(action, "process_name"):
		try:
			contract_v2 = resolve_process_operation_contract_v2(
				_safe_get(action, "process_name"),
				operation,
				process_operation,
				strict=True,
			)
			effective_policy = {
				**effective_policy,
				**(contract_v2.get("policy") or {}),
			}
			config_data = _parse_json_value(_safe_get(action, "config"), {})
			config_schema = contract_v2.get("config_schema") or {}
			if isinstance(config_data, Mapping):
				cleaned_config = _clean_config_for_validation(config_data, config_schema)
				jsonschema_validate(cleaned_config, config_schema)
		except JsonSchemaValidationError as exc:
			errors.append(
				_("Action '{0}' (Process/{1}) config schema validation failed: {2}").format(
					action_label, operation, exc.message
				)
			)
		except Exception as exc:
			errors.append(
				_("Action '{0}' (Process/{1}) contract v2 error: {2}").format(
					action_label, operation, str(exc)
				)
			)

	if mode == "full":
		for fieldname in get_required_fields(action_type):
			if _is_empty(_safe_get(action, fieldname)):
				errors.append(
					_("Action '{0}' ({1}) requires field '{2}'").format(action_label, action_type, fieldname)
				)

	if operation and mode == "full":
		for fieldname in contract.get("mandatory_fields", {}).get(operation, []):
			if _is_empty(_safe_get(action, fieldname)):
				errors.append(
					_("Action '{0}' ({1}) mode '{2}' requires field '{3}'").format(
						action_label, action_type, operation, fieldname
					)
				)

	mutation_mode = _safe_get(action, "mutation_mode")
	if mutation_mode:
		allowed_mutations = effective_policy.get("allowed_mutations") or contract.get("allowed_mutations")
		if allowed_mutations and mutation_mode not in allowed_mutations:
			errors.append(
				_("Action '{0}' ({1}/{2}) does not allow mutation mode '{3}'").format(
					action_label,
					action_type,
					operation or _("default"),
					mutation_mode,
				)
			)

		if allowed_mutations and _is_empty(_safe_get(action, "return_variable")):
			errors.append(
				_("Action '{0}' ({1}) requires Return Variable Name when Mutation Mode is set").format(
					action_label, action_type
				)
			)

	show_return_type = effective_policy.get("show_return_type", contract.get("show_return_type", True))
	return_type = _safe_get(action, "return_type")
	if ((show_return_type and return_type) or _safe_get(action, "resolved_output_schema")) and _is_empty(
		_safe_get(action, "return_variable")
	):
		errors.append(
			_("Action '{0}' ({1}) requires Return Variable Name for Return Schema").format(
				action_label, action_type
			)
		)

	allowed_return_types = effective_policy.get("allowed_return_types") or []

	require_return_type = bool(effective_policy.get("require_return_type"))
	if require_return_type and _is_empty(return_type):
		errors.append(
			_("Action '{0}' ({1}/{2}) requires a return type selection").format(
				action_label,
				action_type,
				operation or _("default"),
			)
		)
	if return_type and allowed_return_types and return_type not in allowed_return_types:
		errors.append(
			_("Action '{0}' ({1}/{2}) does not allow return type '{3}'").format(
				action_label,
				action_type,
				operation or _("default"),
				return_type,
			)
		)

	if bool(effective_policy.get("require_return_variable")) and _is_empty(
		_safe_get(action, "return_variable")
	):
		errors.append(
			_("Action '{0}' ({1}/{2}) requires Return Variable Name").format(
				action_label,
				action_type,
				operation or _("default"),
			)
		)

	config_data = _parse_json_value(_safe_get(action, "config"), {})
	if not isinstance(config_data, Mapping):
		config_data = {}
	if config_data.get("output_mapping") and _is_truthy(_safe_get(action, "is_async")):
		errors.append(
			_("Action '{0}' ({1}) cannot use Output Mapping with Async enabled").format(
				action_label, action_type
			)
		)

	if contract.get("terminal") and (
		_safe_get(action, "next_step_if_true") or _safe_get(action, "next_step_if_false")
	):
		errors.append(
			_("Action '{0}' ({1}) is terminal and should not have next steps").format(
				action_label, action_type
			)
		)

	if not contract.get("has_next_false") and _safe_get(action, "next_step_if_false"):
		errors.append(
			_("Action '{0}' ({1}) does not support 'next step if false'").format(action_label, action_type)
		)

	# Validation based on required_config_keys (from both policy and contract)
	required_config_keys = list(effective_policy.get("required_config_keys") or [])
	if contract.get("required_config_keys"):
		required_config_keys.extend(contract.get("required_config_keys"))

	if required_config_keys:
		config_data = _parse_json_value(_safe_get(action, "config"), {})
		if not isinstance(config_data, Mapping):
			config_data = {}

		for key in required_config_keys:
			value = config_data.get(key)
			if _is_empty(value):
				errors.append(
					_("Action '{0}' ({1}) requires configuration key '{2}'").format(
						action_label, action_type, key
					)
				)


def _validate_action_specifics(
	rule_doc,
	action,
	action_type: str,
	action_label: str,
	warnings: list[str],
	errors: list[str],
) -> None:
	operation = _safe_get(action, "operation")
	config = _parse_json_value(_safe_get(action, "config"), {})

	if action_type == "Process" and _safe_get(action, "process_name"):
		_capture_validation(errors, rule_doc._validate_action_config, action)

	if action_type == "Query Records" and operation == "Query API":
		errors.append(_("Action '{0}' uses removed mode Query API").format(action_label))

	if action_type == "Sub-Rule":
		_capture_validation(errors, rule_doc.validate_sub_rule_target, action)
		if action.rule:
			_validate_sub_rule_input_mapping(action, errors)

	elif action_type == "Condition":
		# Legacy/Specific check if required_config_keys doesn't cover it (e.g. if compiled_expression is used instead)
		if (
			get_condition_payload(action) is None
			and _is_empty(_safe_get(action, "compiled_expression"))
			and "conditions" not in (get_contract(action_type).get("required_config_keys") or [])
		):
			errors.append(_("Action '{0}' is a Condition but no condition is defined.").format(action_label))

	elif action_type == "Switch":
		if not config.get("cases"):
			warnings.append(_("Action '{0}' is a Switch but no cases are defined.").format(action_label))

	elif action_type == "Assignment":
		if hasattr(rule_doc, "_validate_assignment"):
			_capture_validation(errors, rule_doc._validate_assignment, action)
		else:
			_validate_assignment_inline(rule_doc, action, action_label, errors)


def _validate_assignment_inline(rule_doc, action, action_label: str, errors: list[str]) -> None:
	"""Inline assignment validation fallback (used when Rule controller method is unavailable).

	Validates assignment config JSON array — checks targets are doc.* or vars.*,
	that forbidden system paths are not targeted, and that the config is parseable.
	"""
	config_str = _safe_get(action, "config")
	if not config_str:
		return

	try:
		assignments = json.loads(config_str) if isinstance(config_str, str) else config_str
		if not isinstance(assignments, list):
			errors.append(_("Action '{0}': Assignment config must be a JSON array").format(action_label))
			return
	except Exception:
		errors.append(_("Action '{0}': Invalid JSON in Assignment config").format(action_label))
		return

	document_type = _safe_get(rule_doc, "document_type")
	trigger_event = _safe_get(rule_doc, "trigger_event")
	after_submit_events = {"On Submit", "On Update After Submit"}

	for row in assignments:
		if not isinstance(row, dict):
			continue
		target = row.get("target")
		if not target:
			continue

		forbidden_prefixes = ("meta.", "frappe.", "rule.", "caller.")
		if target.startswith(forbidden_prefixes):
			errors.append(
				_("Action '{0}': Cannot assign to protected system path '{1}'").format(action_label, target)
			)
			continue

		if not (target.startswith("doc.") or target.startswith("vars.")):
			errors.append(
				_("Action '{0}': Assignment target '{1}' must start with 'doc.' or 'vars.'").format(
					action_label, target
				)
			)
			continue

		if target.startswith("doc.") and document_type:
			field_path = target[4:]
			base_field = field_path.split(".")[0]
			try:
				meta = frappe.get_meta(document_type)
				df = meta.get_field(base_field)
				if not df:
					errors.append(
						_("Action '{0}': Field '{1}' does not exist on DocType '{2}'").format(
							action_label, base_field, document_type
						)
					)
				elif trigger_event in after_submit_events and df and not df.allow_on_submit:
					errors.append(
						_(
							"Action '{0}': Cannot set field '{1}' after submit. "
							"Field does not have 'Allow on Submit' enabled."
						).format(action_label, target)
					)
			except Exception:
				pass  # Meta lookup failure is non-fatal during validation


def _build_operation_metadata(actions) -> dict:
	metadata = {}
	process_names = {
		_safe_get(action, "process_name")
		for action in actions
		if normalize_action_type(_safe_get(action, "action_type")) == "Process"
		and _safe_get(action, "process_name")
	}

	for process_name in process_names:
		try:
			process = frappe.get_cached_doc("Process", process_name)
		except Exception:
			continue

		for operation in process.get("operations") or []:
			key = f"{process.name}:{_safe_get(operation, 'func_name')}"
			metadata[key] = {
				"reads_vars": _safe_get(operation, "reads_vars"),
				"writes_vars": _safe_get(operation, "writes_vars"),
				"is_terminal": _safe_get(operation, "is_terminal"),
				"writes_to": _safe_get(operation, "writes_to"),
				"can_stop_save": _safe_get(operation, "can_stop_save"),
				"output_schema": _safe_get(operation, "output_schema"),
				"action_overrides": _safe_get(operation, "action_overrides"),
			}

	return metadata


def _validate_variable_dependencies(actions, operation_metadata=None) -> dict:
	errors: list[str] = []
	warnings: list[str] = []
	available_vars = {"doc", "old_doc", "frappe"}
	active_loop_aliases: set[str] = set()  # Track loop aliases to detect shadowing
	operation_metadata = operation_metadata or {}

	for action in actions:
		if _safe_get(action, "action_type") == "Entry Action" or _safe_get(action, "action_id") == "root":
			continue

		if _safe_get(action, "is_enabled") == 0:
			continue

		op_key = f"{_safe_get(action, 'process_name')}:{_safe_get(action, 'operation')}"
		op_meta = operation_metadata.get(op_key, {})
		action_label = _safe_get(action, "action_label") or _safe_get(action, "action_id") or _("(unnamed)")

		reads_vars = _load_json_list(op_meta.get("reads_vars"), warnings, action_label, "reads_vars")
		for var_def in reads_vars:
			var_name = var_def if isinstance(var_def, str) else _safe_get(var_def, "fieldname")
			is_required = 1 if isinstance(var_def, str) else _safe_get(var_def, "reqd", 1)

			if is_required and var_name and var_name not in available_vars:
				errors.append(
					_(
						"Action '{0}' requires variable '{1}' which is not produced by any prior action"
					).format(action_label, var_name)
				)

		writes_vars = _load_json_list(op_meta.get("writes_vars"), warnings, action_label, "writes_vars")
		for var_def in writes_vars:
			var_name = var_def if isinstance(var_def, str) else _safe_get(var_def, "fieldname")
			if var_name:
				available_vars.add(var_name)

		if _safe_get(action, "return_variable"):
			available_vars.add(_safe_get(action, "return_variable"))

		if normalize_action_type(_safe_get(action, "action_type")) == "Loop":
			config = _parse_json_value(_safe_get(action, "config"), {})
			# Use return_variable as alias, fallback to config.alias, then 'item'
			alias = _safe_get(action, "return_variable") or config.get("alias") or "item"

			# Warn on nested loop variable shadowing
			if alias in active_loop_aliases:
				warnings.append(
					_(
						"Action '{0}' uses loop alias '{1}' which shadows an outer loop's alias. "
						"This will overwrite the outer loop's item variable. Use a unique alias."
					).format(action_label, alias)
				)
			active_loop_aliases.add(alias)

			available_vars.add(alias)
			available_vars.add("loop")

	return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}


def _validate_flow_constraints(rule, actions, operation_metadata=None) -> dict:
	errors: list[str] = []
	warnings: list[str] = []
	operation_metadata = operation_metadata or {}
	outgoing: dict[str, list[str]] = {}
	is_active = _is_truthy(_safe_get(rule, "is_active"))

	for action in actions:
		source = _safe_get(action, "action_id") or _safe_get(action, "name")
		if not source:
			continue

		if _safe_get(action, "next_step_if_true"):
			outgoing.setdefault(source, []).append(_safe_get(action, "next_step_if_true"))
		if _safe_get(action, "next_step_if_false"):
			outgoing.setdefault(source, []).append(_safe_get(action, "next_step_if_false"))

	start_action = next(
		(
			action
			for action in actions
			if _safe_get(action, "action_type") == "Entry Action" or _safe_get(action, "action_id") == "root"
		),
		None,
	)
	if start_action:
		reachable = set()
		queue = [_safe_get(start_action, "action_id") or _safe_get(start_action, "name")]

		while queue:
			current = queue.pop(0)
			if not current or current in reachable:
				continue
			reachable.add(current)
			queue.extend(outgoing.get(current, []))

		for action in actions:
			action_id = _safe_get(action, "action_id") or _safe_get(action, "name")
			label = _safe_get(action, "action_label") or action_id or _("(unnamed)")
			if action_id and action_id not in reachable:
				msg = _("Action '{0}' is unreachable from the start node.").format(label)
				if is_active:
					errors.append(msg)
				else:
					# For Drafts, we allow unreachable nodes to enable incremental building
					# warnings.append(msg)
					pass

	for action in actions:
		if _safe_get(action, "action_type") == "Entry Action" or _safe_get(action, "action_id") == "root":
			continue

		action_type = normalize_action_type(_safe_get(action, "action_type"))
		action_id = _safe_get(action, "action_id") or _safe_get(action, "name")
		action_label = _safe_get(action, "action_label") or action_id or _("(unnamed)")
		downstream = outgoing.get(action_id, [])
		op_key = f"{_safe_get(action, 'process_name')}:{_safe_get(action, 'operation')}"
		op_meta = operation_metadata.get(op_key, {})

		if get_contract(action_type).get("terminal") and downstream:
			errors.append(_("{0} is terminal and should not have downstream actions").format(action_label))

		if get_contract(action_type).get("has_next_false") and _is_empty(
			_safe_get(action, "next_step_if_false")
		):
			errors.append(_("Action '{0}' is missing its required false path.").format(action_label))

		if _is_truthy(op_meta.get("is_terminal")) and downstream:
			errors.append(
				_(
					"Action '{0}' is marked as terminal but has downstream actions. Remove connections to: {1}"
				).format(action_label, ", ".join(downstream))
			)

		if op_meta.get("writes_to") == "Database":
			warnings.append(
				_(
					"Action '{0}' writes directly to the database. This is a side-effect that cannot be rolled back."
				).format(action_label)
			)
		elif op_meta.get("writes_to") == "Document":
			warnings.append(
				_("Action '{0}' modifies the document. Ensure this is intentional.").format(action_label)
			)

	return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}


def _load_json_list(value, warnings: list[str], action_label: str, fieldname: str) -> list:
	if not value:
		return []
	try:
		parsed = json.loads(value) if isinstance(value, str) else value
		return parsed if isinstance(parsed, list) else []
	except Exception:
		warnings.append(f"{action_label}: Failed to parse {fieldname}")
		return []


def _validate_json_value(value, label: str, errors: list[str]):
	if not value or not isinstance(value, str):
		return value if value is not None else {}

	try:
		return json.loads(value)
	except json.JSONDecodeError as exc:
		errors.append(_("Invalid JSON in {0}: {1}").format(label, str(exc)))
		return {}


def _parse_json_value(value, default):
	if value is None or value == "":
		return default
	if isinstance(value, Mapping):
		return dict(value)
	try:
		return json.loads(value) if isinstance(value, str) else value
	except Exception:
		return default


def _capture_validation(errors: list[str], fn, *args, **kwargs) -> None:
	try:
		fn(*args, **kwargs)
	except Exception as exc:
		errors.append(str(exc))


def _safe_get(obj, key, default=None):
	if obj is None:
		return default
	if isinstance(obj, Mapping):
		return obj.get(key, default)
	if hasattr(obj, "get"):
		return obj.get(key, default)
	return getattr(obj, key, default)


def _safe_set(obj, key, value) -> None:
	if obj is None:
		return
	if hasattr(obj, "__setitem__"):
		obj[key] = value
		return
	if hasattr(obj, "set"):
		obj.set(key, value)
		return
	setattr(obj, key, value)


def _clean_config_for_validation(data, schema=None):
	"""Remove Frappe/Vue internal UI fields and coerce types before JSON schema validation.

	Frappe Check fields store booleans as integers (0/1), which strict
	JSON Schema validation rejects. When a schema is provided, integer
	values of 0 or 1 are coerced to Python booleans for fields declared
	as type "boolean".
	"""
	INTERNAL_KEYS = frozenset(
		(
			"name",
			"__table_fieldname",
			"__islocal",
			"__checked",
			"idx",
			"parent",
			"parentfield",
			"parenttype",
		)
	)
	if isinstance(data, dict):
		cleaned = {}
		properties = (schema or {}).get("properties", {})
		for k, v in data.items():
			if k in INTERNAL_KEYS:
				continue
			field_schema = properties.get(k)
			cleaned[k] = _clean_config_for_validation(v, field_schema)
		return cleaned
	elif isinstance(data, list):
		items_schema = (schema or {}).get("items")
		return [_clean_config_for_validation(item, items_schema) for item in data]
	# Coerce Frappe Check field integers (0/1) to booleans when schema expects boolean
	if isinstance(data, int) and not isinstance(data, bool) and schema:
		schema_type = schema.get("type")
		if schema_type == "boolean" and data in (0, 1):
			return bool(data)
	return data


def _is_empty(value) -> bool:
	return value in (None, "", [])


def _validate_sub_rule_input_mapping(action, errors: list[str]) -> None:
	"""
	Verify that all variables required by the target sub-rule are mapped
	in the parent action's input_mapping.
	"""
	if not action.rule:
		return

	try:
		target_rule = frappe.get_doc("Rule", action.rule)
	except Exception:
		return

	required_vars = _get_required_variables_for_rule(target_rule)
	if not required_vars:
		return

	config = _parse_json_value(action.config, {})
	input_mapping = config.get("input_mapping", [])
	if not isinstance(input_mapping, list):
		input_mapping = []

	mapped_vars = {m.get("target") for m in input_mapping if m.get("target")}

	missing = [v for v in required_vars if v not in mapped_vars]
	if missing:
		errors.append(
			_("Sub-Rule '{0}' requires input mappings for: {1}").format(
				action.action_label, ", ".join(missing)
			)
		)


def _get_required_variables_for_rule(rule_doc) -> list[str]:
	"""
	Scan a rule for required variables (vars.*) that are not provided
	by the system context or produced within the rule itself before use.
	"""
	required = set()
	available = {"doc", "old_doc", "frappe", "utils"}

	import re

	var_pattern = re.compile(r"\{\{\s*vars\.(\w+)")

	actions = rule_doc.actions or []
	operation_metadata = _build_operation_metadata(actions)

	for action in actions:
		if action.action_type == "Entry Action" or action.action_id == "root":
			continue

		# 1. Check Jinja templates
		templates = [
			getattr(action, "value_template", ""),
		]
		condition_payload = get_condition_payload(action)
		if condition_payload is not None:
			templates.append(json.dumps(condition_payload, ensure_ascii=False))
		else:
			# Legacy fallback while condition_json is deprecated
			templates.append(getattr(action, "condition_json", ""))
		for t in templates:
			if not t or not isinstance(t, str):
				continue
			matches = var_pattern.findall(t)
			for v in matches:
				if v not in available:
					required.add(v)

		# 2. Check Process operations
		op_key = f"{action.process_name}:{action.operation}"
		op_meta = operation_metadata.get(op_key, {})
		reads_vars = _load_json_list(op_meta.get("reads_vars"), [], action.action_label, "reads_vars")
		for var_def in reads_vars:
			var_name = var_def if isinstance(var_def, str) else _safe_get(var_def, "fieldname")
			is_required = 1 if isinstance(var_def, str) else _safe_get(var_def, "reqd", 1)
			if is_required and var_name and var_name not in available:
				required.add(var_name)

		# Update available for next actions
		if action.return_variable:
			available.add(action.return_variable)

		if normalize_action_type(action.action_type) == "Loop":
			config = _parse_json_value(action.config, {})
			# Use return_variable as alias, fallback to config.alias, then 'item'
			alias = getattr(action, "return_variable", None) or config.get("alias") or "item"
			available.add(alias)
			available.add("loop")

		writes_vars = _load_json_list(op_meta.get("writes_vars"), [], action.action_label, "writes_vars")
		for var_def in writes_vars:
			var_name = var_def if isinstance(var_def, str) else _safe_get(var_def, "fieldname")
			if var_name:
				available.add(var_name)

	return sorted(list(required))


def _is_truthy(value) -> bool:
	return value in (1, True, "1")
