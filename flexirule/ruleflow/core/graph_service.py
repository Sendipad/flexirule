# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

"""
Graph Service — Backend-driven graph initialization and validation.

Ensures every Rule has a valid Trigger → End graph structure.
This is the server-side counterpart to the frontend's
useGraphStore.initialize_default_graph().
"""

from __future__ import annotations

import json

import frappe
from frappe import _


def ensure_default_graph(rule_doc) -> bool:
	"""Ensure a rule has at least a valid Trigger → End graph.

	If the rule has no actions and no visual_data, initializes the
	minimum viable graph: Start → End.

	Args:
	    rule_doc: Rule document (Frappe Document)

	Returns:
	    bool: True if graph was initialized, False if already exists
	"""
	actions = rule_doc.get("actions") or []
	visual_data = _parse_visual_data(rule_doc.get("visual_data"))

	if actions or visual_data:
		return False

	# Create Entry Action (Start) node
	start_action = {
		"action_id": "root",
		"action_type": "Entry Action",
		"action_label": "Start",
		"is_enabled": 1,
		"next_step_if_true": "node_end",
		"idx": 1,
	}

	# Create Stop (End) node
	end_action = {
		"action_id": "node_end",
		"action_type": "Stop",
		"action_label": "End",
		"operation": "Success",
		"is_enabled": 1,
		"idx": 2,
	}

	rule_doc.append("actions", start_action)
	rule_doc.append("actions", end_action)

	# Set visual data with default positions
	visual_nodes = [
		{
			"id": "root",
			"type": "start",
			"position": {"x": 250, "y": 50},
			"label": "Start",
			"data": {
				"action_id": "root",
				"action_type": "Entry Action",
				"document_type": rule_doc.document_type,
				"trigger_event": rule_doc.trigger_event,
				"is_enabled": 1,
			},
		},
		{
			"id": "node_end",
			"type": "stop",
			"position": {"x": 250, "y": 200},
			"label": "End",
			"data": {
				"action_id": "node_end",
				"action_type": "Stop",
				"operation": "Success",
				"is_enabled": 1,
			},
		},
	]
	visual_edges = [
		{
			"id": "edge_root_node_end",
			"source": "root",
			"target": "node_end",
			"sourceHandle": "true",
			"animated": True,
		},
	]

	rule_doc.visual_data = json.dumps([*visual_nodes, *visual_edges])
	return True


def get_node_config_schema(
	action_type: str,
	operation: str | None = None,
	process_name: str | None = None,
) -> dict:
	"""Return the full field schema for configuring a node.

	Merges DocType metadata (Rule Action fields) with contract overrides
	to generate a complete, dynamic config form schema.

	Args:
	    action_type: The action type (e.g., "Process", "Condition")
	    operation: Optional operation name
	    process_name: Optional process name (for Process actions)

	Returns:
	    dict: {
	        "fields": [...],
	        "contract": {...},
	        "policy": {...},
	        "sections": [...]
	    }
	"""
	from flexirule.ruleflow.core.contracts import (
		apply_field_overrides,
		get_contract,
		get_effective_action_policy,
		get_operation_field_overrides,
		normalize_action_type,
	)

	action_type = normalize_action_type(action_type)
	contract = get_contract(action_type)

	process_operation = None
	if action_type == "Process" and process_name and operation:
		try:
			process_doc = frappe.get_cached_doc("Process", process_name)
			op_doc = process_doc.get_operation(operation)
			if op_doc:
				process_operation = op_doc.as_dict() if hasattr(op_doc, "as_dict") else op_doc
		except Exception:
			# Keep schema endpoint resilient; policy will fall back to contract defaults.
			process_operation = None

	# Get effective policy for this action_type + operation combo
	policy = get_effective_action_policy(
		action_type,
		operation=operation,
		process_operation=process_operation,
	)

	# Get Rule Action DocType fields
	meta = frappe.get_meta("Rule Action")
	base_fields = []

	# Layout fieldtypes to exclude
	EXCLUDED = {
		"Section Break",
		"Column Break",
		"Tab Break",
		"HTML",
		"Fold",
		"Heading",
	}

	for df in meta.fields:
		if df.fieldtype in EXCLUDED:
			continue

		field_dict = {
			"fieldname": df.fieldname,
			"fieldtype": df.fieldtype,
			"label": df.label,
			"options": df.options,
			"reqd": df.reqd,
			"default": df.default,
			"read_only": df.read_only,
			"hidden": df.hidden,
			"depends_on": df.depends_on,
			"mandatory_depends_on": df.mandatory_depends_on,
			"description": df.description,
			"link_filters": df.link_filters,
		}
		base_fields.append(field_dict)

	# Apply action/operation-specific field override contracts.
	overrides = []
	if action_type in {
		"Entry Action",
		"Condition",
		"Stop",
		"Raise Error",
		"Wait",
		"Sub-Rule",
		"Assignment",
		"Notify",
		"Query Records",
		"Document Action",
	}:
		overrides.extend(get_operation_field_overrides(action_type, "Rule Action", process_operation))
	if operation:
		overrides.extend(get_operation_field_overrides(operation, "Rule Action", process_operation))
	if overrides:
		base_fields = apply_field_overrides(base_fields, overrides)

	# Apply contract-level visibility
	hidden_fields = set(contract.get("hidden_fields", []))
	required_fields = set(contract.get("required_fields", []))

	for field in base_fields:
		fn = field["fieldname"]
		if fn in hidden_fields:
			field["hidden"] = 1
		if fn in required_fields:
			field["reqd"] = 1

	# Apply operation-specific mandatory fields
	if operation and "mandatory_fields" in contract:
		op_mandatory = contract["mandatory_fields"].get(operation, [])
		for field in base_fields:
			if field["fieldname"] in op_mandatory:
				field["reqd"] = 1

	# Organize into logical sections
	sections = _organize_fields_into_sections(base_fields, action_type, contract)

	return {
		"fields": base_fields,
		"contract": {
			"label": contract.get("label", action_type),
			"description": contract.get("description", ""),
			"terminal": contract.get("terminal", False),
			"has_next_false": contract.get("has_next_false", False),
			"operation_options": contract.get("operation_options", []),
			"allowed_mutations": policy.get("allowed_mutations", []),
			"allowed_return_types": policy.get("allowed_return_types", []),
		},
		"policy": policy,
		"sections": sections,
	}


def _organize_fields_into_sections(fields, action_type, contract):
	"""Group fields into logical UI sections.

	Returns a list of section descriptors for the frontend to render as tabs/accordions.
	"""
	sections = [
		{
			"key": "identity",
			"label": _("Identity"),
			"fields": ["action_label", "action_type", "is_enabled"],
		},
		{
			"key": "configuration",
			"label": _("Configuration"),
			"fields": [
				"process_name",
				"operation",
				"config",
				"target_field",
				"value_template",
			],
		},
		{
			"key": "flow",
			"label": _("Flow Control"),
			"description": _("How this action connects to other actions"),
			"fields": [
				"compiled_expression",
				"next_step_if_true",
				"next_step_if_false",
				"on_error",
				"timeout",
				"retry_count",
			],
		},
		{
			"key": "data",
			"label": _("Data"),
			"description": _("Input/output and variable bindings"),
			"fields": [
				"input_source",
				"reference_doctype",
				"reference_docname",
				"mutation_mode",
				"return_type",
				"return_variable",
				"resolved_output_schema",
			],
		},
		{
			"key": "advanced",
			"label": _("Advanced"),
			"fields": [
				"is_async",
				"priority",
				"skip_conditions",
				"ignore_permissions",
			],
		},
	]

	# Filter sections to only include fields that exist and are visible
	visible_fieldnames = {f["fieldname"] for f in fields if not f.get("hidden")}

	result = []
	for section in sections:
		visible_fields = [f for f in section["fields"] if f in visible_fieldnames]
		if visible_fields:
			result.append(
				{
					**section,
					"fields": visible_fields,
				}
			)

	return result


def _parse_visual_data(raw):
	"""Safely parse visual_data field."""
	if not raw:
		return None
	if isinstance(raw, list | dict):
		return raw
	try:
		parsed = json.loads(raw)
		# Empty arrays/dicts are falsy
		return parsed if parsed else None
	except (json.JSONDecodeError, TypeError):
		return None
