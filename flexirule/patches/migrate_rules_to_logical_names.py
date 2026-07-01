# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

import re

import frappe


def execute():
	"""
	Database patch to migrate rules to logical naming and set lineage versions.
	"""
	# 1. Populate base_rule_name for all existing Rules
	rules = frappe.get_all("Rule", fields=["name", "rule_name", "version"])

	# Group rules by base name to resolve previous_version
	lineages: dict[str, list] = {}
	for rule in rules:
		base_name = re.sub(r"_v\d+$", "", rule.rule_name)
		frappe.db.set_value("Rule", rule.name, "base_rule_name", base_name, update_modified=False)
		lineages.setdefault(base_name, []).append(rule)

	# 2. Establish previous_version links based on version hierarchy
	for _, rule_list in lineages.items():
		# Sort by version ascending
		rule_list.sort(key=lambda r: r.version or 0)
		for idx in range(1, len(rule_list)):
			current = rule_list[idx]
			prev = rule_list[idx - 1]
			frappe.db.set_value("Rule", current.name, "previous_version", prev.name, update_modified=False)

	# 3. Update Rule Actions of type Sub-Rule to reference logical base name
	sub_rule_actions = frappe.get_all(
		"Rule Action", filters={"action_type": "Sub-Rule"}, fields=["name", "rule"]
	)

	for action in sub_rule_actions:
		if action.rule:
			logical_name = re.sub(r"_v\d+$", "", action.rule)
			if logical_name != action.rule:
				frappe.db.set_value("Rule Action", action.name, "rule", logical_name, update_modified=False)

	frappe.db.commit()
