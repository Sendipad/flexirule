"""Idempotent registration helpers for app-managed Rule definitions."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

import frappe


def ensure_system_rule(definition: Mapping[str, Any]) -> str:
	"""Create or update a versioned, app-managed Rule definition.

	A user-owned Rule with the same identity is never silently claimed. Definitions
	are applied only when their source version is newer than the stored version.
	"""
	if not isinstance(definition, Mapping):
		frappe.throw("System Rule definition must be a mapping.")

	rule_name = str(definition.get("rule_name") or "").strip()
	source_version = definition.get("system_rule_version")
	if not rule_name:
		frappe.throw("System Rule definition requires rule_name.")
	if not isinstance(source_version, int) or isinstance(source_version, bool) or source_version < 1:
		frappe.throw(f"System Rule '{rule_name}' requires a positive integer system_rule_version.")

	version = cast(int, source_version)
	fields = dict(definition)
	fields.pop("name", None)
	fields["rule_name"] = rule_name
	fields["is_system_generated"] = 1
	fields["system_rule_version"] = version
	fields.setdefault("module", "Ruleflow")

	existing_name = frappe.db.get_value("Rule", {"rule_name": rule_name}, "name")
	if existing_name:
		doc = frappe.get_doc("Rule", existing_name)
		if not doc.get("is_system_generated"):
			frappe.throw(
				f"Cannot register System Rule '{rule_name}': a user-managed Rule already uses that name."
			)
		if int(doc.get("system_rule_version") or 0) >= version:
			return doc.name
	else:
		doc = frappe.new_doc("Rule")

	meta = frappe.get_meta("Rule")
	for fieldname, value in fields.items():
		if fieldname in {"doctype", "name", "owner", "creation", "modified", "modified_by", "docstatus"}:
			continue
		if not meta.has_field(fieldname):
			frappe.throw(f"Unknown field '{fieldname}' in System Rule '{rule_name}'.")
		doc.set(fieldname, value)

	# Installation runs as an administrator; controller validation remains enabled.
	doc.save()
	return doc.name


def ensure_system_rules(definitions: list[Mapping[str, Any]]) -> list[str]:
	"""Register definitions in order and return their document names."""
	return [ensure_system_rule(definition) for definition in definitions]


def register_configured_system_rules() -> list[str]:
	"""Register definitions contributed through the Frappe hook registry.

	Each flexirule_system_rules hook entry is a dotted import path to a callable
	returning an iterable of definition mappings. Definitions stay version-controlled
	with their owning app, and repeated migrations remain safe.
	"""
	names: list[str] = []
	for provider_path in frappe.get_hooks("flexirule_system_rules") or []:
		if not isinstance(provider_path, str) or not provider_path.strip():
			frappe.throw("Each flexirule_system_rules hook must be a dotted provider path.")
		provider = frappe.get_attr(provider_path)
		if not callable(provider):
			frappe.throw(f"System Rule provider '{provider_path}' is not callable.")
		definitions = provider()
		if definitions is None:
			continue
		if not isinstance(definitions, list | tuple):
			frappe.throw(f"System Rule provider '{provider_path}' must return a list or tuple.")
		names.extend(ensure_system_rules(definitions))
	return names
