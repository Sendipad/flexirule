"""Idempotent registration helpers for app-managed Rule definitions.

System Rules are runtime business documents, not DocType schema. Their definitions
are version-controlled by the provider app and synchronized during install/migrate.
The registry intentionally has no second source-version counter: the provider code
is the source of truth for managed definition fields.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import frappe
from frappe import _

_REGISTRATION_FLAG = "flexirule_system_rule_registration"


def ensure_system_rule(definition: Mapping[str, Any]) -> str:
	"""Create or synchronize one app-managed Rule while preserving local enablement."""
	if not isinstance(definition, Mapping):
		frappe.throw(_("System Rule definition must be a mapping."))

	rule_name = str(definition.get("rule_name") or "").strip()
	if not rule_name:
		frappe.throw(_("System Rule definition requires rule_name."))

	fields = dict(definition)
	fields.pop("name", None)
	fields["rule_name"] = rule_name
	fields["is_system_generated"] = 1
	fields.setdefault("module", "Ruleflow")

	existing_name = frappe.db.get_value("Rule", {"rule_name": rule_name}, "name")
	is_existing = bool(existing_name)
	if is_existing:
		doc = frappe.get_doc("Rule", existing_name)
		if not doc.get("is_system_generated"):
			frappe.throw(
				_("Cannot register System Rule '{0}': a user-managed Rule already uses that name.").format(
					rule_name
				)
			)
		# Site operators own activation state. A migration must not silently
		# re-enable a System Rule that an administrator deliberately disabled.
		fields.pop("is_active", None)
		fields.pop("status", None)
	else:
		doc = frappe.new_doc("Rule")

	meta = frappe.get_meta("Rule")
	for fieldname, value in fields.items():
		if fieldname in {"doctype", "name", "owner", "creation", "modified", "modified_by", "docstatus"}:
			continue
		if not meta.has_field(fieldname):
			frappe.throw(_("Unknown field '{0}' in System Rule '{1}'.").format(fieldname, rule_name))
		doc.set(fieldname, value)

	# Scope the bypass to this save only; normal UI/API writes remain guarded.
	previous_flag = getattr(frappe.flags, _REGISTRATION_FLAG, False)
	setattr(frappe.flags, _REGISTRATION_FLAG, True)
	try:
		doc.save(ignore_permissions=True)
	finally:
		setattr(frappe.flags, _REGISTRATION_FLAG, previous_flag)
	return doc.name


def ensure_system_rules(definitions: list[Mapping[str, Any]]) -> list[str]:
	"""Register definitions in order and return their document names."""
	return [ensure_system_rule(definition) for definition in definitions]


def register_configured_system_rules() -> list[str]:
	"""Register definitions contributed through the Frappe hook registry.

	Each flexirule_system_rules hook entry is a dotted import path to a callable
	returning a list/tuple of definition mappings.
	"""
	names: list[str] = []
	for provider_path in frappe.get_hooks("flexirule_system_rules") or []:
		if not isinstance(provider_path, str) or not provider_path.strip():
			frappe.throw(_("Each flexirule_system_rules hook must be a dotted provider path."))
		provider = frappe.get_attr(provider_path)
		if not callable(provider):
			frappe.throw(_("System Rule provider '{0}' is not callable.").format(provider_path))
		definitions = provider()
		if definitions is None:
			continue
		if not isinstance(definitions, list | tuple):
			frappe.throw(_("System Rule provider '{0}' must return a list or tuple.").format(provider_path))
		names.extend(ensure_system_rules(definitions))
	return names
