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
		supports_logical_filter_groups="_parse_nested_filters" in source and "_condition_to_criterion" in source,
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
	if not isinstance(leaf, list | tuple) or len(leaf) not in (2, 3):
		raise ValueError("Legacy Query Builder compatibility supports simple filter leaves only")

	field = leaf[0]
	if not isinstance(field, str) or "." in field:
		raise ValueError("Legacy Query Builder OR compatibility requires root DocType fields")

	if len(leaf) == 2:
		operator, value = "=", leaf[1]
	else:
		operator, value = leaf[1], leaf[2]

	if not isinstance(operator, str):
		raise ValueError("Filter operator must be a string")

	operator = operator.casefold()
	if operator not in OPERATOR_MAP:
		raise ValueError(f"Unsupported filter operator for legacy OR compatibility: {operator}")

	column = frappe.qb.DocType(doctype)[field]
	if isinstance(value, bool):
		value = int(value)
	return OPERATOR_MAP[operator](column, value)


def _compile_logical_filters(doctype: str, filters):
	"""Compile legacy-incompatible AND/OR filter lists into a native Criterion."""
	if not isinstance(filters, list | tuple):
		return filters

	if not any(isinstance(item, str) and item.casefold() in {"and", "or"} for item in filters):
		return filters

	if not filters:
		return None

	criteria: list[Criterion] = []
	pending_operator = "and"
	for item in filters:
		if isinstance(item, str) and item.casefold() in {"and", "or"}:
			pending_operator = item.casefold()
			continue

		criterion = (
			_compile_logical_filters(doctype, item)
			if isinstance(item, list | tuple)
			and any(isinstance(part, str) and part.casefold() in {"and", "or"} for part in item)
			else _criterion_for_leaf(doctype, item)
		)
		if not criteria:
			criteria.append(criterion)
		elif pending_operator == "or":
			criteria[-1] = criteria[-1] | criterion
		else:
			criteria[-1] = criteria[-1] & criterion

	return criteria[0]


def _get_permission_condition(doctype: str, user: str) -> str:
	"""Build Frappe's v15 row-level permission condition without executing a query."""
	from frappe.model.db_query import DatabaseQuery

	permission_query = DatabaseQuery(doctype, user=user)
	permission_query.flags.ignore_permissions = False
	permission_query.reference_doctype = doctype
	return permission_query.build_match_conditions()


def execute_query(doctype: str, kwargs: dict, ignore_permissions: bool):
	"""Execute through native Query Builder with the smallest compatibility shim."""
	query_kwargs = dict(kwargs)

	if not QUERY_CAPABILITIES.supports_logical_filter_groups:
		filters = query_kwargs.get("filters")
		if isinstance(filters, list | tuple) and any(
			isinstance(item, str) and item.casefold() in {"and", "or"} for item in filters
		):
			query_kwargs["filters"] = _compile_logical_filters(doctype, filters)

	if QUERY_CAPABILITIES.supports_ignore_permissions:
		query_kwargs["ignore_permissions"] = ignore_permissions
		query = frappe.qb.get_query(doctype, **query_kwargs)
	else:
		query = frappe.qb.get_query(doctype, **query_kwargs)
		if not ignore_permissions:
			user = frappe.session.user
			Permission.check_permissions(query, user=user)
			permission_condition = _get_permission_condition(doctype, user)
			if permission_condition:
				query = query.where(_TrustedSQLCriterion(permission_condition))

	return query.run(as_dict=True)
