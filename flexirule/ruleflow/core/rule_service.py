# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

"""
Rule Service: Versioning and Amendment Logic

Handles rule versioning, amendment workflows, and lineage queries.
"""

import re
from typing import Any

import frappe
from frappe import _

VERSION_SUFFIX_PATTERN = re.compile(r"_[vV](\d+)$")


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
			"base_rule_name": base_key,
			"status": "Draft",
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
	new_doc.previous_version = original.name

	# Build versioned name
	base_name = _get_rule_base_key(original)
	new_doc.rule_name = f"{base_name}_V{new_doc.version}"
	new_doc.base_rule_name = base_name

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
	rules = frappe.get_all(
		"Rule",
		filters={"base_rule_name": _strip_version_suffix(rule_key)},
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
			"base_rule_name": base_key,
			"status": "Draft",
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
	name_val = getattr(rule_doc, "rule_name", None) or getattr(rule_doc, "name", "")
	return getattr(rule_doc, "base_rule_name", None) or _strip_version_suffix(str(name_val))


def _strip_version_suffix(rule_name: str) -> str:
	"""
	Strip _v{N} version suffix from a rule name.

	e.g. "CUSTOMER_CREDIT_VALIDATION_v3" -> "CUSTOMER_CREDIT_VALIDATION"
	"""
	return VERSION_SUFFIX_PATTERN.sub("", rule_name or "")


def _parse_version_from_name(rule_name: str) -> int | None:
	match = VERSION_SUFFIX_PATTERN.search(rule_name or "")
	return int(match.group(1)) if match else None


def _get_lineage_names(base_key: str) -> list[str]:
	"""
	Get all rule names in a lineage (all versions of the same base rule).
	"""
	return frappe.get_all(
		"Rule",
		filters={"base_rule_name": _strip_version_suffix(base_key)},
		pluck="name",
	)


def resolve_rule_reference(
	rule_ref: str,
	*,
	active_only: bool = False,
	callable_only: bool = False,
	exposed_only: bool = False,
	target_rule_override=None,
) -> str | None:
	"""Resolve a versioned or logical rule reference to a concrete Rule name.

	Versioned references prefer the exact active document for backward
	compatibility. Logical references prefer the active version for the lineage.
	Draft-time validation may fall back to the newest version in the lineage.
	"""
	if not rule_ref:
		return None

	if target_rule_override and (
		getattr(target_rule_override, "name", None) == rule_ref
		or getattr(target_rule_override, "base_rule_name", None) == rule_ref
	):
		return target_rule_override.name

	base_name = _strip_version_suffix(rule_ref)
	is_versioned_ref = bool(VERSION_SUFFIX_PATTERN.search(rule_ref))

	def _matches(doc) -> bool:
		if active_only and not doc.get("is_active"):
			return False
		if callable_only and doc.get("trigger_type") != "Callable Event":
			return False
		if exposed_only and not doc.get("exposed_as_subrule"):
			return False
		return True

	if is_versioned_ref and frappe.db.exists("Rule", rule_ref):
		exact = frappe.db.get_value(
			"Rule",
			rule_ref,
			["name", "is_active", "trigger_type", "exposed_as_subrule"],
			as_dict=True,
		)
		if exact and _matches(exact):
			return exact.name

	filters: dict[str, Any] = {"base_rule_name": base_name}
	if active_only:
		filters["is_active"] = 1
	if callable_only:
		filters["trigger_type"] = "Callable Event"
	if exposed_only:
		filters["exposed_as_subrule"] = 1

	matches = frappe.get_all(
		"Rule",
		filters=filters,
		fields=["name", "version", "modified"],
		order_by="version desc, modified desc",
		limit=1,
	)
	if matches:
		return matches[0].name

	if not active_only and frappe.db.exists("Rule", rule_ref):
		exact = frappe.db.get_value(
			"Rule",
			rule_ref,
			["name", "is_active", "trigger_type", "exposed_as_subrule"],
			as_dict=True,
		)
		if exact and _matches(exact):
			return exact.name

	return None
