# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

"""
Query Records Action Handler

Modes:
- Query List: frappe.get_list() — returns list of dicts
- Query Doc: frappe.get_doc() — returns doc as dict
- Exist Record: frappe.db.exists() — returns boolean
- Query Report: frappe.desk.query_report.run() — returns report data
"""

import json

import frappe
from frappe import _
from frappe.utils import add_days, get_first_day, get_last_day, getdate, nowdate

from flexirule.ruleflow.core.action_handlers import ActionHandler, HandlerRegistry
from flexirule.ruleflow.core.action_handlers.base_contract import (
	AFTER_TRIGGER_EVENTS,
	BROAD_TRIGGER_EVENTS,
	SINGLE_ALLOWED_DOCTYPE_LINK_FILTERS,
	STANDARD_TRIGGER_TYPES,
	VALIDATE_TRIGGER_EVENTS,
	ActionContract,
	OperationContract,
	aggregate_operation_overrides,
	config_depends_on_doctype,
	reference_doctype_override,
	standard_trigger_overrides,
)
from flexirule.ruleflow.core.permissions import can_skip_permissions
from flexirule.ruleflow.utils.mapping import apply_input_mapping


class QueryRecordsHandler(ActionHandler):
	"""Handler for querying records from DocTypes."""

	action_type = "Query Records"

	@classmethod
	def get_action_contract(cls):
		return ActionContract(
			action_type="Query Records",
			required_fields=["reference_doctype", "operation"],
			has_next_true=True,
			has_next_false=False,
			terminal=False,
			css={"icon": "fa fa-search", "color": "#0891b2"},
			operation_label="Query Mode",
			operation_options=[
				"Query List",
				"Query Doc",
				"Exist Record",
				"Query Report",
				"Count",
				"Sum",
				"Average",
				"Min",
				"Max",
				"Group By",
			],
			allowed_mutations=[
				"Set Context Variable",
				"Append to Context Variable",
				"Update Context Variable",
			],
			allowed_return_types=[
				"Yes / No",
				"Single Record",
				"List of Values",
				"List of Records",
			],
			default_return_type="List of Records",
			show_return_type=True,
			require_return_type=False,
			mandatory_fields={
				"Exist Record": ["reference_doctype"],
			},
			operation_policies={
				"Query List": {
					"allowed_return_types": ["List of Records"],
					"default_return_type": "List of Records",
					"show_return_type": False,
					"require_return_type": False,
					"field_labels": {"return_type": "Rows Output Type"},
				},
				"Query Doc": {
					"allowed_return_types": ["Single Record", "Full Document"],
					"default_return_type": "Single Record",
					"show_return_type": True,
					"require_return_type": True,
					"field_labels": {"return_type": "Record Output Type"},
				},
				"Exist Record": {
					"allowed_return_types": ["Yes / No"],
					"default_return_type": "Yes / No",
					"show_return_type": False,
					"require_return_type": False,
					"field_labels": {"return_type": "Boolean Output Type"},
				},
				"Query Report": {
					"allowed_return_types": ["List of Records"],
					"default_return_type": "List of Records",
					"show_return_type": False,
					"require_return_type": False,
					"field_labels": {"return_type": "Report Output Type"},
				},
				"Count": {
					"allowed_return_types": ["List of Values"],
					"default_return_type": "List of Values",
					"show_return_type": False,
					"require_return_type": False,
					"field_labels": {"return_type": "Metric Output Type"},
				},
				"Sum": {
					"allowed_return_types": ["List of Values"],
					"default_return_type": "List of Values",
					"show_return_type": False,
					"require_return_type": False,
					"field_labels": {"return_type": "Metric Output Type"},
				},
				"Average": {
					"allowed_return_types": ["List of Values"],
					"default_return_type": "List of Values",
					"show_return_type": False,
					"require_return_type": False,
					"field_labels": {"return_type": "Metric Output Type"},
				},
				"Min": {
					"allowed_return_types": ["List of Values"],
					"default_return_type": "List of Values",
					"show_return_type": False,
					"require_return_type": False,
					"field_labels": {"return_type": "Metric Output Type"},
				},
				"Max": {
					"allowed_return_types": ["List of Values"],
					"default_return_type": "List of Values",
					"show_return_type": False,
					"require_return_type": False,
					"field_labels": {"return_type": "Metric Output Type"},
				},
				"Group By": {
					"allowed_return_types": ["List of Records"],
					"default_return_type": "List of Records",
					"show_return_type": False,
					"require_return_type": False,
					"field_labels": {"return_type": "Grouped Output Type"},
				},
			},
			field_labels={
				"operation": "Query Mode",
				"reference_doctype": "Target DocType",
				"reference_docname": "Target Record",
				"mutation_mode": "Result Handling",
				"return_type": "Result Type",
			},
			node_type="query",
			category="Data Actions",
			configurable=True,
			config_component="QueryRecordsConfig",
		)

	@classmethod
	def get_operation_contracts(cls) -> dict:
		return {
			"Query List": OperationContract(
				operation="Query List",
				rule_overrides=standard_trigger_overrides(
					trigger_events=BROAD_TRIGGER_EVENTS,
					trigger_types=STANDARD_TRIGGER_TYPES,
				),
				action_overrides=[
					{"fieldname": "action_type", "default": "Query Records"},
					{"fieldname": "operation", "default": "Query List"},
					reference_doctype_override(),
					config_depends_on_doctype(description="Query configuration (filters, sorting)"),
					{
						"fieldname": "mutation_mode",
						"options": [
							"Set Context Variable",
							"Append to Context Variable",
							"Update Context Variable",
						],
						"reqd": 1,
					},
					{"fieldname": "return_type", "default": "List of Records", "read_only": 1},
					{
						"fieldname": "timeout",
						"hidden": "eval:doc.parent.execution_mode!=='Asynchronous'",
						"description": "Only available for async rules",
					},
					{"fieldname": "description", "description": "Queries multiple records from a DocType"},
				],
				validation={"backend": "validate_query_list"},
			),
			"Query Doc": OperationContract(
				operation="Query Doc",
				rule_overrides=standard_trigger_overrides(
					trigger_events=BROAD_TRIGGER_EVENTS,
					trigger_types=STANDARD_TRIGGER_TYPES,
				),
				action_overrides=[
					{"fieldname": "action_type", "default": "Query Records"},
					{"fieldname": "operation", "default": "Query Doc"},
					reference_doctype_override(reqd=0, link_filters=SINGLE_ALLOWED_DOCTYPE_LINK_FILTERS),
					config_depends_on_doctype(),
					{
						"fieldname": "mutation_mode",
						"options": ["Set Context Variable", "Update Context Variable"],
						"reqd": 1,
					},
					{"fieldname": "return_type", "options": ["Single Record", "Full Document"], "reqd": 1},
					{"fieldname": "description", "description": "Queries a single record using filters"},
				],
				validation={"backend": "validate_query_doc"},
			),
			"Exist Record": OperationContract(
				operation="Exist Record",
				rule_overrides=standard_trigger_overrides(
					trigger_events=VALIDATE_TRIGGER_EVENTS,
					trigger_types=STANDARD_TRIGGER_TYPES,
				),
				action_overrides=[
					{"fieldname": "action_type", "default": "Query Records"},
					{"fieldname": "operation", "default": "Exist Record"},
					reference_doctype_override(),
					config_depends_on_doctype(),
					{"fieldname": "return_type", "default": "Yes / No", "read_only": 1},
					{"fieldname": "description", "description": "Checks if records exist matching criteria"},
				],
				validation={"backend": "validate_exist_record"},
			),
			"Query Report": OperationContract(
				operation="Query Report",
				rule_overrides=standard_trigger_overrides(
					trigger_events=AFTER_TRIGGER_EVENTS,
					trigger_types=STANDARD_TRIGGER_TYPES,
				),
				action_overrides=[
					{"fieldname": "action_type", "default": "Query Records"},
					{"fieldname": "operation", "default": "Query Report"},
					reference_doctype_override(),
					config_depends_on_doctype(),
					{"fieldname": "return_type", "default": "List of Records", "read_only": 1},
					{
						"fieldname": "description",
						"description": "Queries records using a custom report configuration",
					},
				],
				validation={"backend": "validate_query_report"},
			),
			"Count": OperationContract(
				operation="Count",
				rule_overrides=standard_trigger_overrides(
					trigger_events=BROAD_TRIGGER_EVENTS,
					trigger_types=STANDARD_TRIGGER_TYPES,
				),
				action_overrides=[
					{"fieldname": "action_type", "default": "Query Records"},
					{"fieldname": "operation", "default": "Count"},
					reference_doctype_override(),
					config_depends_on_doctype(),
					{"fieldname": "return_type", "default": "List of Values", "read_only": 1},
					{"fieldname": "description", "description": "Counts records matching criteria"},
				],
				validation={"backend": "validate_count_records"},
			),
			"Sum": aggregate_operation_overrides("Sum", "Calculates sum of a numeric field"),
			"Average": aggregate_operation_overrides("Average", "Calculates average of a numeric field"),
			"Min": aggregate_operation_overrides("Min", "Finds minimum value of a field"),
			"Max": aggregate_operation_overrides("Max", "Finds maximum value of a field"),
			"Group By": OperationContract(
				operation="Group By",
				rule_overrides=standard_trigger_overrides(
					trigger_events=AFTER_TRIGGER_EVENTS,
					trigger_types=STANDARD_TRIGGER_TYPES,
				),
				action_overrides=[
					{"fieldname": "action_type", "default": "Query Records"},
					{"fieldname": "operation", "default": "Group By"},
					reference_doctype_override(),
					config_depends_on_doctype(),
					{"fieldname": "return_type", "default": "List of Records", "read_only": 1},
					{"fieldname": "description", "description": "Groups records by specified fields"},
				],
				validation={"backend": "validate_group_by_query"},
			),
		}

	def execute(self, action, context, engine):
		"""Execute a query based on the configured mode (operation field)."""
		mode = action.operation
		reference_doctype = action.reference_doctype
		config = self._parse_config(action.config)
		ignore_permissions = can_skip_permissions(action, context, throw=True)

		if not mode:
			frappe.throw(_("Operation/Mode is required for Query Records action"))

		if not reference_doctype:
			frappe.throw(_("Reference DocType is required for Query Records action"))

		# Apply input mapping (Context -> Config)
		action_config = frappe.parse_json(getattr(action, "config", "{}") or "{}")
		if action_config.get("input_mapping"):
			config = apply_input_mapping(context, action_config.get("input_mapping"), config)

		# Dispatch to mode handler
		mode_handlers = {
			"Query List": self._query_list,
			"Query Doc": self._query_doc,
			"Exist Record": self._exist_record,
			"Query Report": self._query_report,
			"Count": self._count_records,
			"Sum": self._aggregate,
			"Average": self._aggregate,
			"Min": self._aggregate,
			"Max": self._aggregate,
			"Group By": self._group_by,
		}

		handler_fn = mode_handlers.get(mode)
		if not handler_fn:
			frappe.throw(_("Unknown Query Records mode: {0}").format(mode))
			raise ValueError("Unknown mode for mypy")

		result = handler_fn(
			reference_doctype=reference_doctype,
			config=config,
			context=context,
			action=action,
			ignore_permissions=ignore_permissions,
		)

		# Determine next action
		next_action = action.next_step_if_true
		return result, next_action

	def validate(self, action, context):
		"""Validate Query Records action configuration."""
		errors = []
		if not action.operation:
			errors.append(_("Operation/Mode is required"))

		mode = action.operation
		if mode == "Query Report":
			config = self._parse_config(action.config)
			if not config.get("report_name"):
				errors.append(_("Query Report mode requires report_name in config"))

		if mode in ("Sum", "Average", "Min", "Max"):
			config = self._parse_config(action.config)
			if not config.get("field"):
				errors.append(_("{0} operation requires 'field' in config").format(mode))
		else:
			config = self._parse_config(action.config)

		if mode != "Query Report" and action.reference_doctype:
			errors.extend(self._validate_doctype_field_references(action.reference_doctype, config))

		if mode == "Query Doc":
			doctype_name = config.get("doctype_name")
			if (
				isinstance(doctype_name, str)
				and not (doctype_name.startswith("{") and doctype_name.endswith("}"))
				and not frappe.db.exists("DocType", doctype_name)
			):
				errors.append(_("DocType {0} does not exist").format(doctype_name))

			if isinstance(doctype_name, dict) and doctype_name.get("mode") == "static":
				dt = doctype_name.get("value")
				if dt and not frappe.db.exists("DocType", dt):
					errors.append(_("DocType {0} does not exist").format(dt))

		return errors

	def _doctype_has_field(self, doctype: str, fieldname: str) -> bool:
		if not doctype or not fieldname:
			return False
		fieldname = str(fieldname).strip()
		if not fieldname:
			return False
		if "." in fieldname:
			parent_field, child_field = fieldname.split(".", 1)
			meta = frappe.get_meta(doctype)
			table_df = meta.get_field(parent_field) if meta else None
			if (
				not table_df
				or table_df.fieldtype not in {"Table", "Table MultiSelect"}
				or not table_df.options
			):
				return False
			child_meta = frappe.get_meta(table_df.options)
			return bool(child_meta and child_meta.has_field(child_field))
		if fieldname in {"name", "owner", "creation", "modified", "modified_by", "docstatus"}:
			return True
		meta = frappe.get_meta(doctype)
		return bool(meta and meta.has_field(fieldname))

	def _is_plain_field_reference(self, token) -> bool:
		if not isinstance(token, str):
			return False
		t = token.strip()
		if not t:
			return False
		if any(x in t.lower() for x in ("(", ")", " as ", "case ", "*", "`")):
			return False
		return True

	def _validate_filter_fields(self, reference_doctype: str, filter_payload) -> list[str]:
		errors: list[str] = []
		if not filter_payload:
			return errors
		rows = filter_payload if isinstance(filter_payload, list) else [filter_payload]
		for row in rows:
			if isinstance(row, dict):
				fieldname = row.get("field") or row.get("fieldname")
				row_dt = row.get("doctype") or reference_doctype
				if (
					fieldname
					and self._is_plain_field_reference(fieldname)
					and not self._doctype_has_field(row_dt, fieldname)
				):
					errors.append(_("Filter field '{0}' does not exist in {1}").format(fieldname, row_dt))
			elif isinstance(row, list):
				if len(row) == 4:
					row_dt, fieldname = row[0], row[1]
				elif len(row) == 3:
					row_dt, fieldname = reference_doctype, row[0]
				else:
					continue
				if self._is_plain_field_reference(fieldname) and not self._doctype_has_field(
					row_dt, fieldname
				):
					errors.append(_("Filter field '{0}' does not exist in {1}").format(fieldname, row_dt))
		return errors

	def _validate_doctype_field_references(self, reference_doctype: str, config: dict) -> list[str]:
		errors: list[str] = []
		if not reference_doctype:
			return errors
		try:
			frappe.get_meta(reference_doctype)
		except Exception:
			return [_("Reference DocType '{0}' does not exist").format(reference_doctype)]

		for f in config.get("fields", []) or []:
			if self._is_plain_field_reference(f) and not self._doctype_has_field(reference_doctype, f):
				errors.append(_("Selected field '{0}' does not exist in {1}").format(f, reference_doctype))

		for key in ("field", "group_by_field", "agg_field"):
			val = config.get(key)
			if (
				val
				and self._is_plain_field_reference(val)
				and not self._doctype_has_field(reference_doctype, val)
			):
				errors.append(
					_("Config field '{0}' references missing field '{1}' in {2}").format(
						key, val, reference_doctype
					)
				)

		order_by = (config.get("order_by") or "").strip()
		if order_by:
			for part in [x.strip() for x in order_by.split(",") if x.strip()]:
				field = part.split(" ")[0].strip()
				if self._is_plain_field_reference(field) and not self._doctype_has_field(
					reference_doctype, field
				):
					errors.append(
						_("Order-by field '{0}' does not exist in {1}").format(field, reference_doctype)
					)

		errors.extend(self._validate_filter_fields(reference_doctype, config.get("filters")))
		errors.extend(self._validate_filter_fields(reference_doctype, config.get("or_filters")))
		return errors

	def _count_records(self, reference_doctype, config, context, action, ignore_permissions):
		"""Count records matching filters using get_list-compatible filters."""
		filters, or_filters = self._resolve_query_filters(config, context, action)
		if not ignore_permissions and not frappe.has_permission(reference_doctype, "read"):
			frappe.throw(
				_("You don't have read permission for {0}").format(reference_doctype), frappe.PermissionError
			)

		# Use get_list/get_all style query so child-table and nested-set operators work consistently.
		rows = frappe.get_all(
			reference_doctype,
			filters=filters,
			or_filters=or_filters,
			fields=["count(name) as _count"],
			ignore_permissions=ignore_permissions,
		)
		return (rows and rows[0].get("_count")) or 0

	def _aggregate(self, reference_doctype, config, context, action, ignore_permissions):
		"""Perform sum/avg/min/max via frappe.get_all for consistent filter semantics."""
		if not ignore_permissions and not frappe.has_permission(reference_doctype, "read"):
			frappe.throw(
				_("You don't have read permission for {0}").format(reference_doctype), frappe.PermissionError
			)

		filters, or_filters = self._resolve_query_filters(config, context, action)
		field = config.get("field", "name")
		mode = action.operation
		agg_map = {
			"Sum": "sum",
			"Average": "avg",
			"Min": "min",
			"Max": "max",
		}
		agg_fn = agg_map.get(mode)
		if not agg_fn:
			frappe.throw(_("Unsupported aggregation mode: {0}").format(mode))

		rows = frappe.get_all(
			reference_doctype,
			filters=filters,
			or_filters=or_filters,
			fields=[f"{agg_fn}({field}) as result"],
			ignore_permissions=ignore_permissions,
		)
		return (rows and rows[0].get("result")) or 0

	def _group_by(self, reference_doctype, config, context, action, ignore_permissions):
		"""Perform group_by aggregation via frappe.get_all for consistent filter semantics."""
		if not ignore_permissions and not frappe.has_permission(reference_doctype, "read"):
			frappe.throw(
				_("You don't have read permission for {0}").format(reference_doctype), frappe.PermissionError
			)

		filters, or_filters = self._resolve_query_filters(config, context, action)
		aggregate_field = config.get("field", "name")
		group_field = config.get("group_by_field", aggregate_field)
		agg_function = config.get("agg_function", "count").lower()
		agg_field = config.get("agg_field", "name")
		safe_agg_fn = agg_function if agg_function in {"sum", "avg", "min", "max", "count"} else "count"
		return frappe.get_all(
			reference_doctype,
			filters=filters,
			or_filters=or_filters,
			fields=[group_field, f"{safe_agg_fn}({agg_field}) as value"],
			group_by=group_field,
			ignore_permissions=ignore_permissions,
		)

	def _safe_eval_with_context(self, expression, context, ref_label: str):
		try:
			return self._safe_eval(expression, context)
		except Exception as e:
			frappe.throw(
				_("Query Records expression failed at {0}: {1}").format(ref_label, str(e)),
				exc=type(e),
			)

	def _resolve_value_expression_with_context(self, value, context, ref_label: str, action=None):
		if isinstance(value, dict):
			if "mode" in value:
				from flexirule.ruleflow.core.value_resolver import get_compiled_resolver

				resolver = get_compiled_resolver(
					action, ref_label.replace(".", "_").replace("[", "_").replace("]", "_"), value
				)
				return resolver.resolve(context)
			return {
				key: self._resolve_value_expression_with_context(val, context, f"{ref_label}.{key}", action)
				for key, val in value.items()
			}
		if isinstance(value, list):
			return [
				self._resolve_value_expression_with_context(v, context, f"{ref_label}[{i}]", action)
				for i, v in enumerate(value)
			]
		if isinstance(value, str) and "{" in value:
			if value.startswith("{") and value.endswith("}") and value.count("{") == 1:
				inner_expr = value[1 : len(value) - 1]
				return self._safe_eval_with_context(inner_expr, context, ref_label)
			import re

			def replace(match):
				expr = match.group(1)
				result = self._safe_eval_with_context(expr, context, ref_label)
				return str(result)

			return re.sub(r"{(.*?)}", replace, value)
		return value

	def _resolve_filters_with_context(self, filters, context, ref_label: str, action=None):
		if not filters:
			return filters
		if isinstance(filters, list):
			resolved_list = []
			for idx, item in enumerate(filters):
				child_ref = f"{ref_label}[{idx}]"
				if isinstance(item, dict) and ("field" in item or "fieldname" in item):
					resolved_list.append(
						{
							k: self._resolve_value_expression_with_context(
								v, context, f"{child_ref}.{k}", action
							)
							for k, v in item.items()
						}
					)
				elif isinstance(item, dict) and "mode" in item:
					resolved_list.append(
						self._resolve_value_expression_with_context(item, context, child_ref, action)
					)
				elif isinstance(item, list | dict):
					resolved_list.append(self._resolve_filters_with_context(item, context, child_ref, action))
				else:
					resolved_list.append(
						self._resolve_value_expression_with_context(item, context, child_ref, action)
					)
			return resolved_list
		if isinstance(filters, dict):
			if "mode" in filters:
				return self._resolve_value_expression_with_context(filters, context, ref_label, action)
			return {
				key: self._resolve_filters_with_context(value, context, f"{ref_label}.{key}", action)
				for key, value in filters.items()
			}
		return self._resolve_value_expression_with_context(filters, context, ref_label, action)

	def _resolve_query_filters(self, config, context, action=None):
		"""Resolve and normalize both filters and or_filters with one shared path."""
		action_label = getattr(action, "label", None) or getattr(action, "action_id", None) or "Query Records"
		filters = self._resolve_filters_with_context(
			config.get("filters"), context, f"{action_label}.filters", action
		)
		filters = self._normalize_filters_for_backend(filters)
		or_filters = config.get("or_filters")
		if or_filters:
			or_filters = self._resolve_filters_with_context(
				or_filters, context, f"{action_label}.or_filters", action
			)
			or_filters = self._normalize_filters_for_backend(or_filters)
		else:
			or_filters = None
		return filters, or_filters

	def _apply_qb_filters(self, query, table, filters):
		"""Helper to apply filters (dict or list) to a query builder object."""
		if isinstance(filters, dict):
			for field, val in filters.items():
				query = self._apply_single_qb_filter(query, table, field, val)
		elif isinstance(filters, list):
			for f in filters:
				if len(f) == 4:
					query = self._apply_single_qb_filter(query, table, f[1], [f[2], f[3]])
				elif len(f) == 3:
					query = self._apply_single_qb_filter(query, table, f[0], [f[1], f[2]])
				elif len(f) == 2:
					query = self._apply_single_qb_filter(query, table, f[0], f[1])
		return query

	def _apply_single_qb_filter(self, query, table, field, value):
		"""Apply a single filter field/value to the query."""
		if isinstance(value, list) and len(value) == 2:
			op, val = value
			if op == "=":
				return query.where(table[field] == val)
			if op == "!=":
				return query.where(table[field] != val)
			if op == ">":
				return query.where(table[field] > val)
			if op == ">=":
				return query.where(table[field] >= val)
			if op == "<":
				return query.where(table[field] < val)
			if op == "<=":
				return query.where(table[field] <= val)
			if op == "like":
				return query.where(table[field].like(val))
			if op == "not like":
				return query.where(table[field].not_like(val))
			if op == "in":
				return query.where(table[field].isin(val))
			if op == "not in":
				return query.where(table[field].notin(val))
			if op == "is":
				if str(val).strip().lower() == "not set":
					return query.where((table[field].isnull()) | (table[field] == ""))
				return query.where((table[field].isnotnull()) & (table[field] != ""))
			if op == "between":
				start, end = self._coerce_between_value(val)
				return query.where(table[field].between(start, end))
		# Default equality
		return query.where(table[field] == value)

	def _coerce_between_value(self, value):
		"""Normalize Between value into [start, end]."""
		if isinstance(value, list | tuple) and len(value) >= 2:
			return value[0], value[1]
		if isinstance(value, str) and "," in value:
			parts = [p.strip() for p in value.split(",", 1)]
			return parts[0], parts[1]
		return value, value

	def _resolve_timespan_range(self, value):
		"""Resolve Frappe-like timespan keyword to date range."""
		token = (value or "").strip().lower()
		today = getdate(nowdate())
		week_start = add_days(today, -today.weekday())
		month_start = get_first_day(today)
		month_end = get_last_day(today)
		next_week_start = add_days(week_start, 7)

		def shift_month(year, month, delta):
			idx = (year * 12 + (month - 1)) + delta
			new_year = idx // 12
			new_month = (idx % 12) + 1
			return new_year, new_month

		if token == "last 7 days":
			return add_days(today, -7), today
		if token == "last 14 days":
			return add_days(today, -14), today
		if token == "last 30 days":
			return add_days(today, -30), today
		if token == "last 90 days":
			return add_days(today, -90), today
		if token == "last week":
			last_week_start = add_days(week_start, -7)
			return last_week_start, add_days(last_week_start, 6)
		if token == "last month":
			last_month_end = add_days(month_start, -1)
			return get_first_day(last_month_end), get_last_day(last_month_end)
		if token == "last quarter":
			current_quarter = ((today.month - 1) // 3) + 1
			if current_quarter == 1:
				year = today.year - 1
				quarter = 4
			else:
				year = today.year
				quarter = current_quarter - 1
			start_month = (quarter - 1) * 3 + 1
			end_month = start_month + 2
			start = getdate(f"{year}-{start_month:02d}-01")
			end = get_last_day(getdate(f"{year}-{end_month:02d}-01"))
			return start, end
		if token == "last 6 months":
			start_year, start_month = shift_month(today.year, today.month, -6)
			start = getdate(f"{start_year}-{start_month:02d}-01")
			return start, today
		if token == "last year":
			return getdate(f"{today.year - 1}-01-01"), getdate(f"{today.year - 1}-12-31")
		if token == "yesterday":
			yesterday = add_days(today, -1)
			return yesterday, yesterday
		if token == "today":
			return today, today
		if token == "tomorrow":
			tomorrow = add_days(today, 1)
			return tomorrow, tomorrow
		if token == "this week":
			return week_start, add_days(week_start, 6)
		if token == "this month":
			return month_start, month_end
		if token == "this quarter":
			quarter_start_month = ((today.month - 1) // 3) * 3 + 1
			quarter_end_month = quarter_start_month + 2
			start = getdate(f"{today.year}-{quarter_start_month:02d}-01")
			end = get_last_day(getdate(f"{today.year}-{quarter_end_month:02d}-01"))
			return start, end
		if token == "this year":
			return getdate(f"{today.year}-01-01"), getdate(f"{today.year}-12-31")
		if token == "next 7 days":
			return today, add_days(today, 7)
		if token == "next 14 days":
			return today, add_days(today, 14)
		if token == "next 30 days":
			return today, add_days(today, 30)
		if token == "next week":
			return next_week_start, add_days(next_week_start, 6)
		if token == "next month":
			year, month = shift_month(today.year, today.month, 1)
			start = getdate(f"{year}-{month:02d}-01")
			return start, get_last_day(start)
		if token == "next quarter":
			current_quarter = ((today.month - 1) // 3) + 1
			if current_quarter == 4:
				year = today.year + 1
				quarter = 1
			else:
				year = today.year
				quarter = current_quarter + 1
			start_month = (quarter - 1) * 3 + 1
			end_month = start_month + 2
			start = getdate(f"{year}-{start_month:02d}-01")
			end = get_last_day(getdate(f"{year}-{end_month:02d}-01"))
			return start, end
		if token == "next 6 months":
			return today, add_days(today, 182)
		if token == "next year":
			return getdate(f"{today.year + 1}-01-01"), getdate(f"{today.year + 1}-12-31")

		# Unknown token => fallback to today
		return today, today

	def _normalize_single_filter_operator(self, op, val):
		"""Normalize UI operators to backend-safe operators/values."""
		if not isinstance(op, str):
			return op, val
		op = op.strip()
		if op == "starts with":
			return "like", f"{val}%"
		if op == "ends with":
			return "like", f"%{val}"
		if op == "Between":
			return "between", val
		if op == "Timespan":
			start, end = self._resolve_timespan_range(val)
			return "between", [start, end]
		return op, val

	def _extract_filter_value_payload(self, value):
		"""
		Support enhanced payload in tuple filters:
		[doctype, field, op, {"value": ..., "value_type": "...", "builder": ...}]
		"""
		if not isinstance(value, dict):
			return value
		if "value" in value:
			raw = value.get("value")
			vtype = (value.get("value_type") or "Value").lower()
			if vtype == "boolean":
				if raw in (True, 1, "1", "Yes", "yes", "true", "True"):
					return 1
				if raw in (False, 0, "0", "No", "no", "false", "False"):
					return 0
			return raw
		return value

	def _normalize_filters_for_backend(self, filters):
		"""Recursively normalize filter operators and emit frappe-style filter tuples."""
		if isinstance(filters, dict):
			normalized = []
			for key, value in filters.items():
				if isinstance(value, list) and len(value) == 2 and isinstance(value[0], str):
					op, val = self._normalize_single_filter_operator(value[0], value[1])
					normalized.append([key, op, val])
				else:
					normalized.append([key, "=", self._normalize_filters_for_backend(value)])
			return normalized

		if isinstance(filters, list):
			normalized_list = []
			for item in filters:
				if isinstance(item, dict) and ("field" in item or "fieldname" in item):
					field = item.get("field") or item.get("fieldname")
					op = item.get("operator", "=")
					val = self._extract_filter_value_payload(item.get("value"))
					doctype = item.get("doctype")
					op, val = self._normalize_single_filter_operator(op, val)
					if doctype:
						normalized_list.append([doctype, field, op, val])
					else:
						normalized_list.append([field, op, val])
					continue
				if isinstance(item, list):
					if len(item) == 4:
						dt, field, op, val = item
						val = self._extract_filter_value_payload(val)
						op, val = self._normalize_single_filter_operator(op, val)
						normalized_list.append([dt, field, op, val])
						continue
					if len(item) == 3:
						field, op, val = item
						val = self._extract_filter_value_payload(val)
						op, val = self._normalize_single_filter_operator(op, val)
						normalized_list.append([field, op, val])
						continue
				normalized_list.append(self._normalize_filters_for_backend(item))
			return normalized_list

		return filters

	def _query_list(self, reference_doctype, config, context, action, ignore_permissions):
		"""Execute frappe.get_list with configured filters, fields, etc."""
		filters, or_filters = self._resolve_query_filters(config, context, action)
		fields = config.get("fields", ["name"])
		limit_type = config.get("limit_type", "Custom Limit")
		if limit_type == "All":
			limit = 0
		elif limit_type == "First Record":
			limit = 1
		else:
			limit_val = config.get("limit")
			if limit_val in (None, ""):
				limit = 20
			else:
				try:
					limit = int(limit_val)
				except ValueError:
					limit = 20
		order_by = config.get("order_by", "modified desc")
		group_by = config.get("group_by")

		kwargs = {
			"doctype": reference_doctype,
			"filters": filters,
			"fields": fields,
			"limit_page_length": limit,
			"order_by": order_by,
			"ignore_permissions": ignore_permissions,
		}
		if or_filters:
			kwargs["or_filters"] = or_filters
		if group_by:
			kwargs["group_by"] = group_by

		return frappe.get_list(**kwargs)

	def _query_doc(self, reference_doctype, config, context, action, ignore_permissions):
		"""Fetch a single document and return as dict."""
		# Prioritize config.doctype_name for newer version, fallback to action.reference_doctype
		raw_doctype = config.get("doctype_name") or reference_doctype

		# Resolve doctype which can be an expression
		resolved_doctype = self._resolve_value_expression_with_context(
			raw_doctype, context, "Query Records.doctype_name", action
		)

		if not resolved_doctype:
			frappe.throw(_("Reference DocType is required for Query Doc"))

		if not frappe.db.exists("DocType", resolved_doctype):
			frappe.throw(_("DocType {0} does not exist").format(resolved_doctype))

		strategy = config.get("fetch_strategy", "Get doc")
		meta = frappe.get_meta(resolved_doctype)
		is_single = meta.issingle

		docname = None
		if strategy == "Get Single DocType":
			if not is_single:
				frappe.throw(_("DocType {0} is not a Single DocType").format(resolved_doctype))
			docname = resolved_doctype
		elif strategy == "Get latest Doc":
			filters, or_filters = self._resolve_query_filters(config, context, action)
			names = frappe.get_all(
				resolved_doctype,
				filters=filters,
				or_filters=or_filters,
				fields=["name"],
				order_by="creation desc",
				limit_page_length=1,
				ignore_permissions=ignore_permissions,
			)
			docname = names[0].name if names else None
		else:
			# Get doc / Get Doc from Cache
			docname = config.get("docname")
			if docname:
				docname = self._resolve_value_expression_with_context(
					docname, context, "Query Records.docname", action
				)

			if not docname and is_single:
				docname = resolved_doctype

		if not docname:
			return None

		fetch_fn = frappe.get_cached_doc if strategy == "Get Doc from Cache" else frappe.get_doc

		try:
			doc = fetch_fn(resolved_doctype, docname)
		except frappe.DoesNotExistError:
			return None

		if not ignore_permissions:
			doc.check_permission("read")

		return doc.as_dict()

	def _exist_record(self, reference_doctype, config, context, action, ignore_permissions):
		"""Check if records exist matching filters. Returns boolean."""
		filters, or_filters = self._resolve_query_filters(config, context, action)

		rows = frappe.get_all(
			reference_doctype,
			filters=filters,
			or_filters=or_filters,
			fields=["name"],
			limit_page_length=1,
			ignore_permissions=ignore_permissions,
		)
		return bool(rows)

	def _query_report(self, reference_doctype, config, context, action, ignore_permissions):
		"""Run a report and return results as a list of dicts."""
		report_name = config.get("report_name")
		if not report_name:
			frappe.throw(_("report_name is required in config for Query Report mode"))

		report_filters, unused = self._resolve_query_filters(config, context, action)

		from frappe.desk.query_report import run as run_report

		result = run_report(
			report_name,
			filters=report_filters,
		)

		data: list = []
		columns: list = []

		if isinstance(result, dict):
			data = result.get("result") or result.get("data") or []
			columns = result.get("columns") or []
		elif isinstance(result, list | tuple) and len(result) >= 2:
			columns = result[0]
			data = result[1]
		elif isinstance(result, list):
			data = result

		# 2. Try to fetch columns from report definition if missing
		if not columns and report_name:
			try:
				report_doc = frappe.get_doc("Report", report_name)
				if report_doc.report_type == "Query Report":
					# Extract columns from query
					pass
				elif report_doc.json:
					report_data = json.loads(report_doc.json)
					columns = report_data.get("columns", [])
			except Exception:
				pass

		# 3. If data is empty, still return columns for schema detection
		if not data:
			return {"columns": columns, "result": []}

		# 4. Transform data (List of Lists/Mixed -> List of Dicts)
		if columns:
			col_names = []
			for col in columns:
				name = None
				if isinstance(col, dict):
					name = col.get("fieldname") or col.get("label")
				elif isinstance(col, str):
					name = col

				if name:
					col_names.append(name)

			if col_names:
				new_data = []
				for row in data:
					if isinstance(row, list | tuple):
						row_dict = {}
						# Handle mixed length or missing columns gracefully
						for i, val in enumerate(row):
							if i < len(col_names):
								row_dict[col_names[i]] = val
						new_data.append(row_dict)
					elif isinstance(row, dict):
						new_data.append(row)
				data = new_data

		return {"columns": columns, "result": data}


# Register handler
HandlerRegistry.register(QueryRecordsHandler())
