# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

"""Metadata-aware validation for condition references.

This module complements the pure condition-tree schema validator with Frappe
DocType metadata checks. It validates references only when their scope has a
known DocType; dynamic variable/context scopes remain data-driven.
"""

from collections.abc import Mapping
from typing import Any

import frappe
from frappe import _

_SYSTEM_FIELDS = frozenset(
	{
		"name",
		"doctype",
		"owner",
		"creation",
		"modified",
		"modified_by",
		"docstatus",
		"idx",
		"parent",
		"parenttype",
		"parentfield",
	}
)


def validate_condition_metadata(
	tree: Any,
	doctype: str | None = None,
	context: Mapping | None = None,
) -> None:
	"""Reject known-scope field paths that do not exist in Frappe metadata."""
	scope_doctypes: dict[str, str] = {}
	if doctype:
		scope_doctypes.update({"doc": doctype, "old_doc": doctype})

	if isinstance(context, Mapping):
		for scope in ("doc", "old_doc", "row", "item", "loop"):
			source = context.get(scope)
			source_doctype = _read(source, "doctype")
			if source_doctype:
				scope_doctypes[scope] = str(source_doctype)

	_walk_node(tree, scope_doctypes)


def _walk_node(node: Any, scope_doctypes: dict[str, str]) -> None:
	if isinstance(node, list):
		for child in node:
			_walk_node(child, scope_doctypes)
		return
	if not isinstance(node, Mapping):
		return

	if "collection" in node and "where" in node:
		nested_scopes = dict(scope_doctypes)
		alias = node.get("alias", "row")
		child_doctype = _resolve_collection_doctype(node.get("collection"), scope_doctypes)
		if child_doctype:
			nested_scopes["row"] = child_doctype
			nested_scopes[str(alias)] = child_doctype
		_walk_node(node.get("where"), nested_scopes)
		return

	children = node.get("conditions")
	if isinstance(children, list):
		for child in children:
			_walk_node(child, scope_doctypes)
		return

	for operand_name in ("left", "right"):
		_validate_operand(node.get(operand_name), scope_doctypes, operand_name)


def _validate_operand(operand: Any, scope_doctypes: dict[str, str], path: str) -> None:
	if not isinstance(operand, Mapping):
		return
	if "ref" in operand:
		_validate_reference(operand.get("ref"), scope_doctypes, path)
		return

	value = operand.get("value")
	if not isinstance(value, Mapping):
		return

	mode = value.get("mode")
	if mode == "variable":
		_validate_reference(value.get("path") or value.get("value"), scope_doctypes, f"{path}.value.path")
		return

	if mode == "expression":
		segments = value.get("value")
		if not isinstance(segments, list):
			return
		for index, segment in enumerate(segments):
			if not isinstance(segment, Mapping) or segment.get("type") != "variableToken":
				continue
			attrs = segment.get("attrs") or {}
			if isinstance(attrs, Mapping):
				_validate_reference(
					attrs.get("path"),
					scope_doctypes,
					f"{path}.value.value[{index}].attrs.path",
				)


def _validate_reference(reference: Any, scope_doctypes: dict[str, str], path: str) -> None:
	if not isinstance(reference, str) or "." not in reference:
		return

	scope, field_path = reference.split(".", 1)
	doctype = scope_doctypes.get(scope)
	if not doctype or not field_path:
		return
	_resolve_field(doctype, field_path, f"{path} ({reference})")


def _resolve_collection_doctype(reference: Any, scope_doctypes: dict[str, str]) -> str | None:
	if not isinstance(reference, str) or "." not in reference:
		return None
	scope, field_path = reference.split(".", 1)
	doctype = scope_doctypes.get(scope)
	if not doctype or not field_path:
		return None
	field = _resolve_field(doctype, field_path, f"collection ({reference})")
	if _read(field, "fieldtype") in {"Table", "Table MultiSelect"}:
		options = _read(field, "options")
		return str(options) if options else None
	return None


def _resolve_field(doctype: str, field_path: str, path: str) -> Any:
	try:
		meta = frappe.get_meta(doctype)
	except Exception as exc:
		raise ValueError(
			_("Could not load metadata for DocType {0} while validating {1}.").format(doctype, path)
		) from exc

	parts = field_path.split(".")
	field = None
	for index, fieldname in enumerate(parts):
		if fieldname in _SYSTEM_FIELDS:
			if index == len(parts) - 1:
				return None
			if fieldname == "parent" and getattr(meta, "istable", False):
				return None

		field = meta.get_field(fieldname)
		if field is None:
			raise ValueError(
				_("{0}: field {1!r} does not exist on DocType {2!r}.").format(
					path, fieldname, getattr(meta, "name", None) or doctype
				)
			)

		if index == len(parts) - 1:
			return field

		fieldtype = _read(field, "fieldtype")
		options = _read(field, "options")
		if fieldtype in {"Table", "Table MultiSelect", "Link"} and options:
			try:
				meta = frappe.get_meta(options)
			except Exception as exc:
				raise ValueError(
					_("Could not load linked DocType metadata for {0} while validating {1}.").format(
						options, path
					)
				) from exc
		elif fieldtype == "Dynamic Link":
			# Its target DocType is determined by record data, not static metadata.
			return None
		else:
			raise ValueError(
				_("{0}: field {1!r} on DocType {2!r} cannot be traversed to another field.").format(
					path, fieldname, doctype
				)
			)

	return field


def _read(target: Any, key: str) -> Any:
	if target is None:
		return None
	if isinstance(target, Mapping):
		return target.get(key)
	getter = getattr(target, "get", None)
	if callable(getter):
		return getter(key)
	return getattr(target, key, None)
