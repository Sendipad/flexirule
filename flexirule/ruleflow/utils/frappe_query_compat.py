# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

"""Compatibility helpers for Frappe Query Builder capabilities."""

from dataclasses import dataclass
from inspect import getsource, signature

import frappe
from frappe.database.operator_map import OPERATOR_MAP
from frappe.database.query import Engine, Permission
from frappe.query_builder import Criterion


@dataclass(frozen=True)
class FrappeQueryCapabilities:
	"""Static capabilities of the installed Frappe Query Builder API."""

	supports_ignore_permissions: bool
	supports_logical_filter_groups: bool


def detect_query_capabilities() -> FrappeQueryCapabilities:
	"""Detect Query Builder keyword capabilities once during module initialization."""
	parameters = signature(Engine.get_query).parameters
	source = getsource(Engine.apply_filters)
	return FrappeQueryCapabilities(
		supports_ignore_permissions="ignore_permissions" in parameters,
		supports_logical_filter_groups="_parse_nested_filters" in source
		and "_condition_to_criterion" in source,
	)


QUERY_CAPABILITIES = detect_query_capabilities()


class _TrustedSQLCriterion(Criterion):
	"""Render SQL produced by Frappe's own permission compiler.

	The SQL is never assembled from FlexiRule input. It comes from Frappe's
	DatabaseQuery permission machinery and is therefore treated as trusted.
	"""

	def __init__(self, sql: str):
		self.sql = sql

	def get_sql(self, **kwargs):
		return self.sql


def _criterion_for_leaf(doctype: str, leaf):
	"""Compile one simple filter using Frappe/Pypika operators."""
	if not isinstance(leaf, list | tuple) or len(leaf) not in (2, 3, 4):
		raise ValueError("Legacy Query Builder compatibility supports simple filter leaves only")

	if len(leaf) == 4:
		leaf_dt, field, operator, value = leaf[0], leaf[1], leaf[2], leaf[3]
	elif len(leaf) == 3:
		leaf_dt, field, operator, value = doctype, leaf[0], leaf[1], leaf[2]
	else:
		leaf_dt, field, operator, value = doctype, leaf[0], "=", leaf[1]

	if not isinstance(field, str) or "." in field:
		raise ValueError("Legacy Query Builder OR compatibility requires root DocType fields")

	if not isinstance(operator, str):
		raise ValueError("Filter operator must be a string")

	operator = operator.casefold()
	if operator not in OPERATOR_MAP:
		raise ValueError(f"Unsupported filter operator for legacy OR compatibility: {operator}")

	column = frappe.qb.DocType(leaf_dt or doctype)[field]
	if isinstance(value, bool):
		value = int(value)
	return OPERATOR_MAP[operator](column, value)


def _compile_filter_tree(filters, default_doctype: str):
	"""Compile FlexiRule's canonical filter tree into Frappe's nested QB filter form.

	The persisted contract is intentionally independent of Frappe. At runtime the
	canonical group/leaf AST is lowered to the nested filter syntax understood by
	Frappe v15's Engine, which then converts nested conditions into Pypika
	Criterion objects. This preserves arbitrary AND/OR nesting without exposing
	Frappe's filter representation to the UI/config contract.
	"""
	if filters in (None, "", []):
		return None

	def leaf_to_condition(node):
		if not isinstance(node, dict) or node.get("type") != "leaf":
			raise ValueError("Filter tree leaf must be an object with type='leaf'")

		doctype = node.get("doctype") or default_doctype
		field = node.get("field")
		operator = node.get("operator") or "="
		if not doctype:
			raise ValueError("Filter tree leaf requires a DocType")
		if not isinstance(field, str) or not field.strip():
			raise ValueError("Filter tree leaf requires a field")
		if not isinstance(operator, str) or not operator.strip():
			raise ValueError("Filter tree leaf requires an operator")

		return [doctype, field, operator, node.get("value")]

	def visit(node):
		if not isinstance(node, dict):
			raise ValueError("Filter tree node must be an object")

		if node.get("type") == "leaf":
			return leaf_to_condition(node)

		if node.get("type") != "group":
			raise ValueError("Filter tree node type must be 'group' or 'leaf'")

		operator = str(node.get("operator") or "and").lower()
		if operator not in {"and", "or"}:
			raise ValueError("Filter tree group operator must be 'and' or 'or'")

		children = node.get("children") or []
		if not isinstance(children, list):
			raise ValueError("Filter tree group children must be a list")
		if not children:
			return None

		compiled = [visit(child) for child in children]
		compiled = [child for child in compiled if child is not None]
		if not compiled:
			return None
		if len(compiled) == 1:
			return compiled[0]

		result = [compiled[0]]
		for child in compiled[1:]:
			result.extend([operator, child])
		return result

	return visit(filters)


def _get_permission_condition(doctype: str, user: str) -> str:
	"""Build Frappe's v15 row-level permission condition without executing a query."""
	from frappe.model.db_query import DatabaseQuery

	permission_query = DatabaseQuery(doctype, user=user)
	permission_query.flags.ignore_permissions = False
	permission_query.reference_doctype = doctype
	return permission_query.build_match_conditions()


def execute_query(doctype: str, kwargs: dict, ignore_permissions: bool):
	"""Build a Frappe Query Builder query and enforce permissions separately."""
	query_kwargs = dict(kwargs)

	filters = query_kwargs.get("filters")
	if isinstance(filters, dict) and filters.get("type") in {"group", "leaf"}:
		query_kwargs["filters"] = _compile_filter_tree(filters, doctype)

	# Frappe v15's get_query() is a SQL builder, not a permission API. Always
	# perform permission checking as a separate step and never pass
	# ignore_permissions/user through get_query().
	query = frappe.qb.get_query(doctype, **query_kwargs)
	if not ignore_permissions:
		user = frappe.session.user
		try:
			Permission.check_permissions(query, user=user)
		except frappe.ValidationError as e:
			if "Insufficient Permission" in str(e):
				raise frappe.PermissionError(e)
			raise

	return query.run(as_dict=True)
