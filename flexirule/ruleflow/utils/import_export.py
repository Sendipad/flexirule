# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

"""
Rule Import/Export utilities
"""

import json

import frappe
from frappe import _


def export_rule(rule_name):
	"""
	Export a rule to JSON format

	Args:
	    rule_name: Name of rule to export

	Returns:
	    dict: Exportable rule data
	"""
	rule = frappe.get_doc("Rule", rule_name)

	export_data = {
		"flexirule_version": "1.0",
		"export_date": frappe.utils.now(),
		"rule": {
			"rule_name": rule.rule_name,
			"document_type": rule.document_type,
			"trigger_event": rule.trigger_event,
			"rule_type": getattr(rule, "rule_type", None),
			"priority": rule.priority,
			"is_active": rule.is_active,
			"conditions_json": getattr(rule, "conditions_json", None),
			"options_json": getattr(rule, "options_json", None),
			"visual_data": getattr(rule, "visual_data", None),
			"actions": [],
		},
	}

	# Export actions
	for action in rule.actions:
		export_data["rule"]["actions"].append(
			{
				"action_id": action.action_id,
				"action_label": action.action_label,
				"action_type": action.action_type,
				"is_enabled": action.is_enabled,
				"configuration": action.config,
				"compiled_expression": action.compiled_expression,
				"on_error": action.on_error,
				"next_step_if_true": action.next_step_if_true,
				"next_step_if_false": action.next_step_if_false,
				"position_x": action.position_x,
				"position_y": action.position_y,
			}
		)

	return export_data


def import_rule(import_data, overwrite=False):
	"""
	Import a rule from JSON format

	Args:
	    import_data: dict or JSON string of exported rule
	    overwrite: Whether to overwrite existing rule

	Returns:
	    str: Name of imported rule
	"""
	if isinstance(import_data, str):
		import_data = json.loads(import_data)

	rule_data = import_data.get("rule", {})
	rule_name = rule_data.get("rule_name")

	if not rule_name:
		frappe.throw(_("Invalid import data: missing rule_name"))

	# Check if exists
	exists = frappe.db.exists("Rule", {"rule_name": rule_name})

	if exists and not overwrite:
		frappe.throw(_("Rule '{0}' already exists. Set overwrite=True to replace.").format(rule_name))

	if exists:
		rule = frappe.get_doc("Rule", exists)
		# Clear existing actions
		rule.actions = []
	else:
		rule = frappe.new_doc("Rule")

	# Set rule fields
	for field in [
		"rule_name",
		"document_type",
		"trigger_event",
		"rule_type",
		"priority",
		"is_active",
		"conditions_json",
		"options_json",
		"visual_data",
	]:
		if field in rule_data:
			rule.set(field, rule_data[field])

	# Add actions
	for action_data in rule_data.get("actions", []):
		if action_data.get("condition_expression") and not action_data.get("compiled_expression"):
			action_data["compiled_expression"] = action_data.pop("condition_expression")
		rule.append("actions", action_data)

	rule.save()

	return rule.name


def export_rules_bulk(rule_names=None, filters=None):
	"""Export multiple rules"""
	if rule_names:
		rules = rule_names
	elif filters:
		rules = frappe.get_all("Rule", filters=filters, pluck="name")
	else:
		rules = frappe.get_all("Rule", pluck="name")

	return {
		"flexirule_version": "1.0",
		"export_date": frappe.utils.now(),
		"rules": [export_rule(r)["rule"] for r in rules],
	}


def import_rules_bulk(import_data, overwrite=False):
	"""Import multiple rules"""
	if isinstance(import_data, str):
		import_data = json.loads(import_data)

	imported = []
	for rule_data in import_data.get("rules", []):
		try:
			name = import_rule({"rule": rule_data}, overwrite)
			imported.append(name)
		except Exception as e:
			frappe.log_error(f"Failed to import rule: {e!s}")

	return imported
