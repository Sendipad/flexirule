"""Idempotent registration helpers for app-managed Rule definitions.

System Rules are runtime business documents, not DocType schema. Their definitions
are version-controlled by the provider app and synchronized during install/migrate.
The registry uses Rule's existing version lineage instead of a second source-version
counter, and never silently mutates an active or previously published definition.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from contextlib import contextmanager
from typing import Any

import frappe
from frappe import _

_REGISTRATION_FLAG = "flexirule_system_rule_registration"
_SAVEPOINT_NAME = "flexirule_system_rules_batch"

_DOCUMENT_METADATA_FIELDS = {
	"doctype",
	"name",
	"owner",
	"creation",
	"modified",
	"modified_by",
	"docstatus",
	"idx",
	"parent",
	"parentfield",
	"parenttype",
}

_REGISTRY_OWNED_FIELDS = {
	"base_rule_name",
	"previous_version",
	"version",
	"is_system_generated",
	"is_active",
	"status",
}


@contextmanager
def _system_rule_registration():
	"""Scope the registry bypass to the exact synchronization operation."""
	previous_flag = getattr(frappe.flags, _REGISTRATION_FLAG, False)
	setattr(frappe.flags, _REGISTRATION_FLAG, True)
	try:
		yield
	finally:
		setattr(frappe.flags, _REGISTRATION_FLAG, previous_flag)


def _field_values_match(current: Any, desired: Any, field) -> bool:
	"""Compare provider-owned values without treating Frappe metadata as source data."""
	fieldtype = getattr(field, "fieldtype", None)

	if fieldtype in {"Table", "Table MultiSelect"}:
		current_rows = list(current or [])
		desired_rows = desired or []
		if not isinstance(desired_rows, list | tuple):
			frappe.throw(
				_("System Rule table field '{0}' must be a list of row mappings.").format(field.fieldname)
			)
		if len(current_rows) != len(desired_rows):
			return False

		child_meta = frappe.get_meta(field.options)
		for current_row, desired_row in zip(current_rows, desired_rows, strict=True):
			if not isinstance(desired_row, Mapping):
				frappe.throw(
					_("System Rule table field '{0}' contains a row that is not a mapping.").format(
						field.fieldname
					)
				)
			for child_fieldname, child_value in desired_row.items():
				if child_fieldname in _DOCUMENT_METADATA_FIELDS:
					continue
				if not child_meta.has_field(child_fieldname):
					frappe.throw(
						_("Unknown child field '{0}' in System Rule table '{1}'.").format(
							child_fieldname, field.fieldname
						)
					)
				child_field = child_meta.get_field(child_fieldname)
				if not _field_values_match(current_row.get(child_fieldname), child_value, child_field):
					return False
		return True

	if fieldtype == "Check":
		return bool(current) == bool(desired)

	if current in (None, "") and desired in (None, ""):
		return True

	# Code/JSON and structured provider values are compared semantically so that
	# harmless JSON whitespace or key ordering does not trigger a new Rule version.
	if fieldtype in {"Code", "JSON"} or isinstance(desired, Mapping | list | tuple):

		def decode_json(value):
			if not isinstance(value, str):
				return value
			try:
				return json.loads(value)
			except (TypeError, ValueError):
				return value

		return decode_json(current) == decode_json(desired)

	return current == desired


def _validate_nested_field(field, value: Any, rule_name: str, field_path: str) -> None:
	"""Validate provider child rows against their actual Frappe DocType schema."""
	if field.fieldtype not in {"Table", "Table MultiSelect"}:
		return

	if not isinstance(value, list | tuple):
		frappe.throw(
			_("System Rule field '{0}' must be a list of row mappings.").format(field_path)
		)

	child_meta = frappe.get_meta(field.options)
	for row_index, row in enumerate(value):
		if not isinstance(row, Mapping):
			frappe.throw(
				_("System Rule field '{0}' row {1} must be a mapping.").format(field_path, row_index + 1)
			)
		for child_fieldname, child_value in row.items():
			if child_fieldname in _DOCUMENT_METADATA_FIELDS:
				continue
			if not child_meta.has_field(child_fieldname):
				frappe.throw(
					_("Unknown field '{0}' in System Rule '{1}' ({2}, row {3}).").format(
						child_fieldname, rule_name, field_path, row_index + 1
					)
				)
			child_field = child_meta.get_field(child_fieldname)
			_validate_nested_field(
				child_field,
				child_value,
				rule_name,
				f"{field_path}[{row_index + 1}].{child_fieldname}",
			)


def _validate_definition_fields(fields: Mapping[str, Any], rule_name: str) -> None:
	"""Reject misspelled provider fields and malformed child rows before writing."""
	meta = frappe.get_meta("Rule")
	for fieldname, value in fields.items():
		if fieldname in _DOCUMENT_METADATA_FIELDS or fieldname in _REGISTRY_OWNED_FIELDS:
			continue
		if fieldname == "rule_name":
			continue
		if not meta.has_field(fieldname):
			frappe.throw(_("Unknown field '{0}' in System Rule '{1}'.").format(fieldname, rule_name))
		field = meta.get_field(fieldname)
		_validate_nested_field(field, value, rule_name, fieldname)


def _find_system_rule(logical_name: str):
	"""Return the latest document in a managed Rule lineage, or reject ownership conflicts."""
	exact_name = frappe.db.get_value("Rule", {"rule_name": logical_name}, "name")
	if exact_name and not frappe.db.get_value("Rule", exact_name, "is_system_generated"):
		frappe.throw(
			_("Cannot register System Rule '{0}': a user-managed Rule already uses that name.").format(
				logical_name
			)
		)

	lineage = frappe.get_all(
		"Rule",
		filters={"base_rule_name": logical_name},
		fields=["name", "version", "is_system_generated", "status", "is_active", "modified"],
		order_by="version desc, modified desc",
	)
	lineage_names = {row.get("name") for row in lineage}
	if exact_name and exact_name not in lineage_names:
		lineage.append(
			{
				"name": exact_name,
				"version": frappe.db.get_value("Rule", exact_name, "version") or 1,
				"is_system_generated": 1,
				"status": frappe.db.get_value("Rule", exact_name, "status"),
				"is_active": frappe.db.get_value("Rule", exact_name, "is_active"),
				"modified": frappe.db.get_value("Rule", exact_name, "modified"),
			}
		)

	for row in lineage:
		if not row.get("is_system_generated"):
			frappe.throw(
				_(
					"Cannot register System Rule '{0}': Rule '{1}' in its version lineage is user-managed."
				).format(logical_name, row.get("name"))
			)

	if not lineage:
		return None

	latest = max(lineage, key=lambda row: int(row.get("version") or 1))
	return frappe.get_doc("Rule", latest.get("name"))


def ensure_system_rule(definition: Mapping[str, Any]) -> str:
	"""Create or synchronize one app-managed Rule while preserving operator state.

	An unchanged existing version is a true no-op. Source changes to a published
	version create a normal Rule amendment and leave the current active/disabled
	version untouched; the new version remains Draft until an operator activates it.
	"""
	if not isinstance(definition, Mapping):
		frappe.throw(_("System Rule definition must be a mapping."))

	logical_name = str(definition.get("rule_name") or "").strip()
	if not logical_name:
		frappe.throw(_("System Rule definition requires rule_name."))

	fields = dict(definition)
	fields.pop("name", None)
	fields.pop("doctype", None)
	fields["rule_name"] = logical_name
	fields["is_system_generated"] = 1
	fields.setdefault("module", "Ruleflow")

	# Lifecycle, lineage, and ownership fields are managed by the registry or site
	# operators, never by provider definitions.
	for fieldname in _REGISTRY_OWNED_FIELDS:
		fields.pop(fieldname, None)

	_validate_definition_fields(fields, logical_name)

	with _system_rule_registration():
		doc = _find_system_rule(logical_name)
		if not doc:
			doc = frappe.new_doc("Rule")
			for fieldname, value in fields.items():
				if fieldname in _DOCUMENT_METADATA_FIELDS:
					continue
				if fieldname == "is_system_generated":
					continue
				if not frappe.get_meta("Rule").has_field(fieldname):
					frappe.throw(
						_("Unknown field '{0}' in System Rule '{1}'.").format(fieldname, logical_name)
					)
				doc.set(fieldname, value)
			# App-managed Rules begin as drafts; installation must never activate one.
			doc.is_system_generated = 1
			doc.is_active = 0
			doc.status = "Draft"
			doc.save(ignore_permissions=True)
			return doc.name

		source_fields = {fieldname: value for fieldname, value in fields.items() if fieldname != "rule_name"}
		meta = frappe.get_meta("Rule")
		has_source_changes = any(
			not _field_values_match(doc.get(fieldname), value, meta.get_field(fieldname))
			for fieldname, value in source_fields.items()
		)
		if not has_source_changes:
			# In particular, don't call save() on an unchanged Active Rule: Frappe
			# correctly rejects edits to active definitions.
			return doc.name

		if doc.is_active or doc.status != "Draft":
			from flexirule.ruleflow.core.rule_service import amend_rule

			draft_name = amend_rule(doc.name)
			doc = frappe.get_doc("Rule", draft_name)

		# rule_name is a stable provider identity, but published versions use
		# Frappe's existing _V<N> naming and lineage. Never rename a version back
		# to the provider's logical name during reconciliation.
		for fieldname, value in source_fields.items():
			if fieldname in _DOCUMENT_METADATA_FIELDS or fieldname in _REGISTRY_OWNED_FIELDS:
				continue
			if not meta.has_field(fieldname):
				frappe.throw(_("Unknown field '{0}' in System Rule '{1}'.").format(fieldname, logical_name))
			doc.set(fieldname, value)

		doc.is_system_generated = 1
		doc.save(ignore_permissions=True)
		return doc.name


def ensure_system_rules(definitions: list[Mapping[str, Any]]) -> list[str]:
	"""Register definitions atomically and return their document names."""
	frappe.db.savepoint(_SAVEPOINT_NAME)
	try:
		return [ensure_system_rule(definition) for definition in definitions]
	except Exception:
		frappe.db.rollback(save_point=_SAVEPOINT_NAME)
		raise


def register_configured_system_rules() -> list[str]:
	"""Register definitions contributed through the Frappe hook registry.

	Each flexirule_system_rules hook entry is a dotted import path to a callable
	returning a list/tuple of definition mappings. Provider evaluation completes
	before any records are written, then the combined batch is synchronized atomically.
	"""
	definitions: list[Mapping[str, Any]] = []
	for provider_path in frappe.get_hooks("flexirule_system_rules") or []:
		if not isinstance(provider_path, str) or not provider_path.strip():
			frappe.throw(_("Each flexirule_system_rules hook must be a dotted provider path."))
		provider = frappe.get_attr(provider_path)
		if not callable(provider):
			frappe.throw(_("System Rule provider '{0}' is not callable.").format(provider_path))
		provided_definitions = provider()
		if provided_definitions is None:
			continue
		if not isinstance(provided_definitions, list | tuple):
			frappe.throw(_("System Rule provider '{0}' must return a list or tuple.").format(provider_path))
		definitions.extend(provided_definitions)

	return ensure_system_rules(definitions)
