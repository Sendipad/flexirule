# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

"""
Rule Service: Versioning and Amendment Logic

Handles rule versioning, amendment workflows, and lineage queries.
"""

import frappe
from frappe import _


def amend_rule(rule_name: str) -> str:
	"""
	Create a new version of a rule by copying it.

	The original rule stays active. The copy becomes a draft amendment
	with an incremented version number.

	Args:
	    rule_name: Name of the rule to amend.

	Returns:
	    Name of the new (amended) rule document.

	Raises:
	    frappe.ValidationError: If a draft amendment already exists.
	"""
	original = frappe.get_doc("Rule", rule_name)

	# Check if a draft copy already exists for this lineage
	base_key = _get_rule_base_key(original)
	existing_draft = frappe.db.exists(
		"Rule",
		{
			"is_active": 0,
			"rule_name": ["like", f"{base_key}%"],
			"name": ["!=", rule_name],
		},
	)
	if existing_draft:
		frappe.throw(_("A draft amendment already exists for this rule: {0}").format(existing_draft))

	# Copy the document
	new_doc = frappe.copy_doc(original)
	new_doc.is_active = 0
	new_doc.status = "Draft"
	new_doc.version = (original.version or 1) + 1
	new_doc.last_error = None

	# Build versioned name
	base_name = _strip_version_suffix(original.rule_name)
	new_doc.rule_name = f"{base_name}_v{new_doc.version}"

	new_doc.insert(ignore_permissions=True)
	return new_doc.name


def get_latest_rule_version(rule_key: str) -> dict | None:
	"""
	Get the latest version of a rule by its base name (without version suffix).

	Args:
	    rule_key: Base name of the rule (e.g., "CUSTOMER_CREDIT_VALIDATION").

	Returns:
	    Dict with name, version, is_active, or None if not found.
	"""
	# Find all rules in this lineage
	rules = frappe.get_all(
		"Rule",
		filters={"rule_name": ["like", f"{rule_key}%"]},
		fields=["name", "rule_name", "version", "is_active"],
		order_by="version desc",
		limit=1,
	)

	return rules[0] if rules else None


def validate_single_draft_copy(rule_doc):
	"""
	Ensure only one draft amendment exists per rule lineage.
	"""
	base_key = _get_rule_base_key(rule_doc)

	other_drafts = frappe.get_all(
		"Rule",
		filters={
			"rule_name": ["like", f"{base_key}%"],
			"is_active": 0,
			"name": ["!=", rule_doc.name],
		},
		pluck="name",
	)

	if other_drafts:
		frappe.throw(
			_("Only one draft amendment is allowed per rule lineage. Existing draft: {0}").format(
				other_drafts[0]
			)
		)


def _get_rule_base_key(rule_doc) -> str:
	"""
	Extract the base name from a rule, stripping the _v{N} suffix.
	"""
	return _strip_version_suffix(rule_doc.rule_name)


def _strip_version_suffix(rule_name: str) -> str:
	"""
	Strip _v{N} version suffix from a rule name.

	e.g. "CUSTOMER_CREDIT_VALIDATION_v3" -> "CUSTOMER_CREDIT_VALIDATION"
	"""
	import re

	return re.sub(r"_v\d+$", "", rule_name)


def _get_lineage_names(base_key: str) -> list[str]:
	"""
	Get all rule names in a lineage (all versions of the same base rule).
	"""
	return frappe.get_all(
		"Rule",
		filters={"rule_name": ["like", f"{base_key}%"]},
		pluck="name",
	)
