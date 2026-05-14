# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

"""
Rule versioning hooks - uses Frappe's built-in Version tracking
"""

import json

import frappe


def get_rule_versions(rule_name, limit=20):
	"""Get version history for a rule"""
	versions = frappe.get_all(
		"Version",
		filters={"ref_doctype": "Rule", "docname": rule_name},
		fields=["name", "creation", "owner", "data"],
		order_by="creation desc",
		limit=limit,
	)

	result = []
	for v in versions:
		try:
			data = json.loads(v.data) if v.data else {}
			changes = []

			# Parse changes
			for row in data.get("changed", []):
				changes.append({"field": row[0], "old": row[1], "new": row[2]})

			result.append(
				{
					"version": v.name,
					"created": v.creation,
					"user": v.owner,
					"changes": changes,
				}
			)
		except Exception:
			pass

	return result


def restore_rule_version(rule_name, version_name):
	"""Restore a rule to a previous version"""
	version = frappe.get_doc("Version", version_name)

	if version.ref_doctype != "Rule" or version.docname != rule_name:
		frappe.throw("Invalid version for this rule")

	# Get saved state
	data = json.loads(version.data)

	# Restore rule
	rule = frappe.get_doc("Rule", rule_name)

	for row in data.get("changed", []):
		field, old_value, _new_value = row
		# Restore old value
		rule.set(field, old_value)

	rule.save()

	return True
