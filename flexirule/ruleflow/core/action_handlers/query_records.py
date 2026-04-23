# Copyright (c) 2026, Bolton and contributors
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
from flexirule.ruleflow.core.permissions import can_skip_permissions
from flexirule.ruleflow.utils.mapping import apply_input_mapping


class QueryRecordsHandler(ActionHandler):
	"""Handler for querying records from DocTypes."""

	action_type = "Query Records"

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
		if not action.reference_doctype:
			errors.append(_("Reference DocType is required"))

		mode = action.operation
		if mode == "Query Doc" and not action.reference_docname:
			config = self._parse_config(action.config)
			if not config.get("docname") and not config.get("docname_expression"):
				errors.append(
					_(
						"Query Doc mode requires either a Reference Document or a docname/docname_expression in config"
					)
				)

		if mode == "Query Report":
			config = self._parse_config(action.config)
			if not config.get("report_name"):
				errors.append(_("Query Report mode requires report_name in config"))

		if mode in ("Sum", "Average", "Min", "Max"):
			config = self._parse_config(action.config)
			if not config.get("field"):
				errors.append(_("{0} operation requires 'field' in config").format(mode))

		return errors

	def _count_records(self, reference_doctype, config, context, action, ignore_permissions):
		"""Count records matching filters."""
		filters = self._resolve_filters(config.get("filters", {}), context)
		filters = self._normalize_filters_for_backend(filters)
		# Skip permission check is already handled by frappe.db functions if we don't pass ignore_permissions arg to them,
		# actually frappe.db.count doesn't take ignore_permissions. We check read permission manually if needed.
		if not ignore_permissions and not frappe.has_permission(reference_doctype, "read"):
			frappe.throw(
				_("You don't have read permission for {0}").format(reference_doctype), frappe.PermissionError
			)

		return frappe.db.count(reference_doctype, filters=filters)

	def _aggregate(self, reference_doctype, config, context, action, ignore_permissions):
		"""Perform sum/avg/min/max aggregation using frappe.qb."""
		from frappe.query_builder import DocType
		from frappe.query_builder.functions import Avg, Max, Min, Sum

		if not ignore_permissions and not frappe.has_permission(reference_doctype, "read"):
			frappe.throw(
				_("You don't have read permission for {0}").format(reference_doctype), frappe.PermissionError
			)

		filters = self._resolve_filters(config.get("filters", {}), context)
		filters = self._normalize_filters_for_backend(filters)
		field = config.get("field", "name")
		mode = action.operation

		table = DocType(reference_doctype)

		agg_functions = {
			"Sum": Sum,
			"Average": Avg,
			"Min": Min,
			"Max": Max,
		}

		agg_fn = agg_functions[mode]
		query = frappe.qb.from_(table).select(agg_fn(table[field]).as_("result"))
		query = self._apply_qb_filters(query, table, filters)

		result = query.run(as_dict=True)
		return result[0]["result"] if result else 0

	def _group_by(self, reference_doctype, config, context, action, ignore_permissions):
		"""Perform group_by aggregation."""
		from frappe.query_builder import DocType
		from frappe.query_builder.functions import Avg, Count, Max, Min, Sum

		if not ignore_permissions and not frappe.has_permission(reference_doctype, "read"):
			frappe.throw(
				_("You don't have read permission for {0}").format(reference_doctype), frappe.PermissionError
			)

		filters = self._resolve_filters(config.get("filters", {}), context)
		filters = self._normalize_filters_for_backend(filters)
		aggregate_field = config.get("field", "name")
		group_field = config.get("group_by_field", aggregate_field)
		agg_function = config.get("agg_function", "count").lower()
		agg_field = config.get("agg_field", "name")

		table = DocType(reference_doctype)

		agg_functions = {
			"sum": Sum,
			"avg": Avg,
			"min": Min,
			"max": Max,
			"count": Count,
		}

		agg_fn = agg_functions.get(agg_function, Count)
		query = (
			frappe.qb.from_(table)
			.select(table[group_field], agg_fn(table[agg_field]).as_("value"))
			.groupby(table[group_field])
		)

		query = self._apply_qb_filters(query, table, filters)
		return query.run(as_dict=True)

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
				if op == "starts with":
					return query.where(table[field].like(f"{val}%"))
				if op == "ends with":
					return query.where(table[field].like(f"%{val}"))
				if op == "in":
					return query.where(table[field].isin(val))
			if op == "not in":
				return query.where(table[field].notin(val))
			if op in ("Between", "between"):
				start, end = self._coerce_between_value(val)
				return query.where(table[field].between(start, end))
			if op == "Timespan":
				start, end = self._resolve_timespan_range(val)
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
		if op == "starts with":
			return "like", f"{val}%"
		if op == "ends with":
			return "like", f"%{val}"
		return op, val

	def _normalize_filters_for_backend(self, filters):
		"""Recursively normalize filter operators for get_list/count/exists/qb compatibility."""
		if isinstance(filters, dict):
			normalized = {}
			for key, value in filters.items():
				if isinstance(value, list) and len(value) == 2 and isinstance(value[0], str):
					op, val = self._normalize_single_filter_operator(value[0], value[1])
					normalized[key] = [op, val]
				else:
					normalized[key] = self._normalize_filters_for_backend(value)
			return normalized

		if isinstance(filters, list):
			normalized_list = []
			for item in filters:
				if isinstance(item, list):
					if len(item) == 4:
						dt, field, op, val = item
						op, val = self._normalize_single_filter_operator(op, val)
						normalized_list.append([dt, field, op, val])
						continue
					if len(item) == 3:
						field, op, val = item
						op, val = self._normalize_single_filter_operator(op, val)
						normalized_list.append([field, op, val])
						continue
				normalized_list.append(self._normalize_filters_for_backend(item))
			return normalized_list

		return filters

	def _query_list(self, reference_doctype, config, context, action, ignore_permissions):
		"""Execute frappe.get_list with configured filters, fields, etc."""
		filters = config.get("filters", {})
		or_filters = config.get("or_filters", {})
		fields = config.get("fields", ["name"])
		limit = config.get("limit", 20)
		order_by = config.get("order_by", "modified desc")
		group_by = config.get("group_by")

		# Resolve template expressions in filters
		filters = self._resolve_filters(filters, context)
		filters = self._normalize_filters_for_backend(filters)
		if or_filters:
			or_filters = self._resolve_filters(or_filters, context)
			or_filters = self._normalize_filters_for_backend(or_filters)

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
		docname = action.reference_docname or config.get("docname")

		# Support dynamic docname from expression
		if not docname and config.get("docname_expression"):
			docname = self._safe_eval(config["docname_expression"], context)

		if not docname:
			frappe.throw(_("No document name specified for Query Doc"))

		doc = frappe.get_doc(reference_doctype, docname)
		if not ignore_permissions:
			doc.check_permission("read")

		return doc.as_dict()

	def _exist_record(self, reference_doctype, config, context, action, ignore_permissions):
		"""Check if records exist matching filters. Returns boolean."""
		filters = config.get("filters", {})
		filters = self._resolve_filters(filters, context)
		filters = self._normalize_filters_for_backend(filters)

		exists = frappe.db.exists(reference_doctype, filters)
		return bool(exists)

	def _query_report(self, reference_doctype, config, context, action, ignore_permissions):
		"""Run a report and return results as a list of dicts."""
		report_name = config.get("report_name")
		if not report_name:
			frappe.throw(_("report_name is required in config for Query Report mode"))

		report_filters = config.get("filters", {})
		report_filters = self._resolve_filters(report_filters, context)
		report_filters = self._normalize_filters_for_backend(report_filters)

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
