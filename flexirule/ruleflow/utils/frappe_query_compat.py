# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

"""Compatibility helpers for Frappe Query Builder capabilities."""

from dataclasses import dataclass
from inspect import signature

import frappe
from frappe.database.query import Engine, Permission
from frappe.query_builder import Criterion


@dataclass(frozen=True)
class FrappeQueryCapabilities:
	"""Static capabilities of the installed Frappe Query Builder API."""

	supports_ignore_permissions: bool


def detect_query_capabilities() -> FrappeQueryCapabilities:
	"""Detect Query Builder keyword capabilities once during module initialization."""
	parameters = signature(Engine.get_query).parameters
	return FrappeQueryCapabilities(
		supports_ignore_permissions="ignore_permissions" in parameters,
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
