# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

"""
Query Records Action Handler

Modes:
- Query List: frappe.get_list() — returns list of dicts
- Query Doc: frappe.get_doc() — returns doc as dict
- Exist Record: frappe.db.exists() — returns boolean
- Query Report: frappe.desk.query_report.run() — returns report data
- Fetch Records: frappe.qb.get_query() — returns list of dicts via Frappe Query Builder
"""

import json
from typing import Any, ClassVar

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
from flexirule.ruleflow.core.permissions import can_ignore_permissions
from flexirule.ruleflow.utils.mapping import apply_input_mapping


class QueryRecordsHandler(ActionHandler):
	"""Handler for querying records from DocTypes."""

	action_type = "Query Records"

	@classmethod
	def get_action_contract(cls):
		return ActionContract(
			action_type="Query Records",
			display_label="Query Records",
			required_fields=["reference_doctype", "operation"],
			has_next_true=True,
			has_next_false=False,
			terminal=False,
			css={"icon": "fa fa-search", "color": "#0891b2"},
			operation_label="Query Mode",
			operation_options=[
				"Fetch Records",
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
				"Fetch Records": {
					"allowed_return_types": ["List of Records"],
					"default_return_type": "List of Records",
					"show_return_type": False,
					"require_return_type": False,
					"field_labels": {"return_type": "Rows Output Type"},
				},
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
		contracts = {
			"Fetch Records": OperationContract(
				operation="Fetch Records",
				rule_overrides=standard_trigger_overrides(
					trigger_events=BROAD_TRIGGER_EVENTS,
					trigger_types=STANDARD_TRIGGER_TYPES,
				),
				action_overrides=[
					{"fieldname": "action_type", "default": "Query Records"},
					{"fieldname": "operation", "default": "Fetch Records"},
					reference_doctype_override(),
					{"fieldname": "reference_docname", "hidden": 1, "reqd": 0},
					config_depends_on_doctype(description="Frappe Query Builder configuration"),
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
					{
						"fieldname": "description",
						"description": "Queries records using Frappe Query Builder (frappe.qb.get_query)",
					},
				],
				validation={"backend": "validate_fetch_records"},
			),
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
					{"fieldname": "reference_docname", "hidden": 1, "reqd": 0},
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
					{"fieldname": "reference_doctype", "default": "Report", "read_only": 1},
					{
						"fieldname": "reference_docname",
						"label": "Report Name",
						"options": "Report",
						"reqd": 1,
						"hidden": 0,
					},
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

		permission_overrides = [
			{
				"fieldname": "ignore_permissions",
				"read_only": "eval:!frappe.user.has_role('System Manager')",
			},
			{
				"fieldname": "permission_audit_reason",
				"mandatory_depends_on": "ignore_permissions",
				"hidden": "eval:!doc.ignore_permissions",
			},
		]

		for op in contracts.values():
			op.action_overrides.extend(permission_overrides)

		return contracts

	def execute(self, action, context, engine):
		"""Execute a query based on the configured mode (operation field)."""
		mode = action.operation
		reference_doctype = action.reference_doctype
		config = self._parse_config(action.config)
		ignore_permissions = can_ignore_permissions(action, context, throw=True)

		if not mode:
			frappe.throw(_("Operation/Mode is required for Query Records action"))

		if not reference_doctype:
			reference_doctype = config.get("doctype_name")

		if not reference_doctype:
			frappe.throw(_("Reference DocType is required for Query Records action"))

		# Apply input mapping (Context -> Config)
		action_config = frappe.parse_json(getattr(action, "config", "{}") or "{}")
		if action_config.get("input_mapping"):
			config = apply_input_mapping(context, action_config.get("input_mapping"), config)

		# Dispatch to mode handler
		mode_handlers = {
			"Fetch Records": self._fetch_records,
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
		if mode == "Fetch Records":
			config = self._parse_config(action.config)
			errors.extend(self.validate_fetch_records(action, config))
			if action.reference_doctype:
				errors.extend(self._validate_doctype_field_references(action.reference_doctype, config))
			return errors

		if mode == "Query Report":
			if action.reference_doctype != "Report":
				errors.append(_("Query Report mode requires reference_doctype to be 'Report'"))
			if not action.reference_docname:
				errors.append(_("Query Report mode requires a target Report Name"))
			elif not frappe.db.exists("Report", action.reference_docname):
				errors.append(_("Report '{0}' does not exist").format(action.reference_docname))

			config = self._parse_config(action.config)
			if not config.get("report_name"):
				# Synchronize report_name inside config to reference_docname
				config["report_name"] = action.reference_docname

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
			try:
				meta = frappe.get_meta(doctype)
				df = meta.get_field(parent_field) if meta else None
				if df and df.fieldtype in {"Table", "Table MultiSelect", "Link"} and df.options:
					return self._doctype_has_field(df.options, child_field)
			except Exception:
				pass
			return False
		if fieldname in {"name", "owner", "creation", "modified", "modified_by", "docstatus"}:
			return True
		try:
			meta = frappe.get_meta(doctype)
			return bool(meta and meta.has_field(fieldname))
		except Exception:
			return False

	def validate_fetch_records(self, action, config: dict) -> list[str]:
		"""Validate only stable FlexiRule-level inputs for Fetch Records.

		Field expressions and the complete native filters payload are deliberately
		left to frappe.qb.get_query so this operation does not fork Frappe's query
		language or relationship-resolution behavior.
		"""
		ref_dt = action.reference_doctype or config.get("doctype_name")
		if not ref_dt:
			return [_("Reference DocType is required for Fetch Records")]

		try:
			frappe.get_meta(ref_dt)
		except Exception:
			return [_("Reference DocType '{0}' does not exist").format(ref_dt)]

		errors = []
		filters = config.get("filters")
		if filters not in (None, "", []) and self._is_canonical_filter_tree(filters):
			errors.extend(self._validate_canonical_fetch_filter_tree(filters))
		for key in ("limit", "offset"):
			value = config.get(key)
			if value in (None, "") or (
				isinstance(value, str) and (value.strip().startswith("{") or value.strip().startswith("@"))
			):
				continue
			if not isinstance(value, str | int | float):
				errors.append(_("{0} must be an integer").format(key.replace("_", " ").title()))
				continue
			try:
				parsed = int(value)
			except (TypeError, ValueError):
				errors.append(_("{0} must be an integer").format(key.replace("_", " ").title()))
				continue
			if parsed < 0:
				errors.append(_("{0} must be a non-negative integer").format(key.replace("_", " ").title()))

		distinct = config.get("distinct")
		if distinct is not None and not isinstance(distinct, bool | int):
			if isinstance(distinct, str) and distinct.lower() not in ("true", "false", "0", "1"):
				errors.append(_("Distinct must be a boolean value"))

		return errors

	_FETCH_RECORDS_OPERATORS: ClassVar[set[str]] = {
		"=",
		"!=",
		"<>",
		">",
		">=",
		"<",
		"<=",
		"like",
		"not like",
		"in",
		"not in",
		"between",
		"not between",
		"is",
		"is set",
		"is not set",
		"timespan",
		"starts with",
		"ends with",
		"descendants of",
		"ancestors of",
	}

	def _validate_canonical_fetch_filter_tree(self, node, path="filters") -> list[str]:
		"""Validate Fetch Records' persisted tree contract; never accept legacy filter shapes."""
		errors = []
		if not isinstance(node, dict):
			return [_("{0} must be a canonical filter group or leaf").format(path)]
		node_type = node.get("type")
		if node_type == "group":
			operator = node.get("operator")
			children = node.get("children")
			if not isinstance(operator, str) or operator.lower() not in {"and", "or"}:
				errors.append(_("{0}.operator must be 'and' or 'or'").format(path))
			if not isinstance(children, list) or not children:
				errors.append(_("{0}.children must be a non-empty list").format(path))
			else:
				for index, child in enumerate(children):
					errors.extend(
						self._validate_canonical_fetch_filter_tree(child, f"{path}.children[{index}]")
					)
			return errors
		if node_type != "leaf":
			return [_("{0}.type must be 'group' or 'leaf'").format(path)]
		field = node.get("field")
		if not isinstance(field, str) or not field.strip():
			errors.append(_("{0}.field is required").format(path))
		operator = node.get("operator")
		if not isinstance(operator, str) or operator.strip().lower() not in self._FETCH_RECORDS_OPERATORS:
			errors.append(_("{0}.operator is not supported").format(path))
		value = node.get("value")
		if "value" not in node:
			errors.append(_("{0}.value is required (use null for an explicit NULL)").format(path))
		elif (
			isinstance(value, dict)
			and "mode" in value
			and value.get("mode")
			not in {"static", "link", "dynamic_link", "variable", "resolver", "expression", "jinja"}
		):
			errors.append(_("{0}.value.mode is not supported").format(path))
		elif isinstance(value, dict) and "mode" in value:
			mode = value.get("mode")
			if mode in {"static", "link", "dynamic_link", "expression", "jinja"} and "value" not in value:
				errors.append(_("{0}.value.value is required for {1} values").format(path, mode))
			elif mode == "variable" and not (value.get("path") or "value" in value):
				errors.append(_("{0}.value.path is required for variable values").format(path))
			elif mode == "resolver" and not any(key in value for key in ("config", "kind", "family")):
				errors.append(_("{0}.value requires resolver config, kind, or family").format(path))
		if isinstance(value, dict) and value.get("mode") == "static" and "value" in value:
			operator_name = operator.strip().lower() if isinstance(operator, str) else ""
			static_value = value.get("value")
			if operator_name in {"between", "not between"} and not (
				isinstance(static_value, list | tuple) and len(static_value) == 2
			):
				errors.append(_("{0}.value for Between must contain exactly two values").format(path))
			if operator_name in {"in", "not in"} and not isinstance(static_value, list | tuple | str):
				errors.append(_("{0}.value for IN/NOT IN must be a list or string").format(path))
		return errors

	def _fetch_records(self, reference_doctype, config, context, action, ignore_permissions):
		"""Execute Fetch Records through Frappe's native Query Builder API.

		FlexiRule resolves dynamic values only. Frappe owns field parsing, joins,
		filter semantics, validation, and query-level permission enforcement.
		"""
		action_label = getattr(action, "label", None) or getattr(action, "action_id", None) or "Query Records"

		def resolve_payload(value, path):
			"""Resolve FlexValue payloads recursively without changing native QB structure."""
			if isinstance(value, dict):
				if "mode" in value:
					return self._resolve_value_expression_with_context(value, context, path, action)
				return {key: resolve_payload(item, f"{path}.{key}") for key, item in value.items()}
			if isinstance(value, list):
				return [resolve_payload(item, f"{path}[{index}]") for index, item in enumerate(value)]
			if isinstance(value, tuple):
				return tuple(resolve_payload(item, f"{path}[{index}]") for index, item in enumerate(value))
			if isinstance(value, str):
				return self._resolve_value_expression_with_context(value, context, path, action)
			return value

		filters = config.get("filters")
		if filters not in (None, "", []):
			if not self._is_canonical_filter_tree(filters):
				frappe.throw(_("Fetch Records filters must use the canonical filter tree format"))
			filter_errors = self._validate_canonical_fetch_filter_tree(filters)
			if filter_errors:
				frappe.throw("; ".join(filter_errors))

		kwargs = {}
		if config.get("fields") not in (None, "", []):
			kwargs["fields"] = resolve_payload(config["fields"], f"{action_label}.fields")

		for key in ("filters", "order_by", "group_by", "limit", "offset", "distinct"):
			value = config.get(key)
			if value is None or value == "":
				continue
			if key == "filters" and self._is_canonical_filter_tree(value):
				# Resolve only leaf values. Recursively resolving every string in the
				# persisted tree corrupts structural tokens such as "group", "and",
				# field names, and DocType names.
				value = self._resolve_fetch_filter_tree_values(
					value, context, f"{action_label}.filters", action
				)
				value = self._canonical_fetch_filter_tree_to_backend(value, reference_doctype)
			else:
				value = resolve_payload(value, f"{action_label}.{key}")
			kwargs[key] = value

		from flexirule.ruleflow.utils.frappe_query_compat import execute_query

		return execute_query(
			reference_doctype,
			kwargs,
			ignore_permissions,
		)

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
		"""Validate filter fields recursively, including nested AND/OR trees."""
		errors: list[str] = []

		def validate_leaf(fieldname, row_dt=None):
			row_dt = row_dt or reference_doctype
			if (
				fieldname
				and self._is_plain_field_reference(fieldname)
				and not self._doctype_has_field(row_dt, fieldname)
			):
				errors.append(_("Filter field '{0}' does not exist in {1}").format(fieldname, row_dt))

		def visit(node):
			if node is None:
				return

			if isinstance(node, dict):
				if node.get("type") == "group":
					for child in node.get("children") or []:
						visit(child)
					return
				fieldname = node.get("field") or node.get("fieldname")
				if fieldname:
					validate_leaf(fieldname, node.get("doctype") or reference_doctype)
					return
				for key, value in node.items():
					if str(key).lower() in ("and", "or"):
						visit(value)
					elif self._is_plain_field_reference(key):
						validate_leaf(key)
				return

			if isinstance(node, list | tuple):
				if (
					len(node) in (2, 3, 4)
					and isinstance(node[0], str)
					and node[0].lower() not in ("and", "or")
				):
					if len(node) == 4:
						validate_leaf(node[1], node[0] or reference_doctype)
					else:
						validate_leaf(node[0], reference_doctype)
					return

				for item in node:
					if isinstance(item, str) and item.lower() in ("and", "or"):
						continue
					visit(item)

		visit(filter_payload)
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
		"""Count records matching filters using get_list with permission enforcement."""
		filters, or_filters = self._resolve_query_filters(
			config, context, action, reference_doctype=reference_doctype
		)

		rows = frappe.get_list(
			reference_doctype,
			filters=filters,
			or_filters=or_filters,
			fields=[f"count(distinct `tab{reference_doctype}`.name) as _count"],
			ignore_permissions=ignore_permissions,
			limit_page_length=0,
		)
		return (rows and rows[0].get("_count")) or 0

	def _aggregate(self, reference_doctype, config, context, action, ignore_permissions):
		"""Perform sum/avg/min/max via frappe.get_list with permission enforcement."""
		filters, or_filters = self._resolve_query_filters(
			config, context, action, reference_doctype=reference_doctype
		)
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

		field_dt, field_name = self._resolve_filter_doctype_and_field(reference_doctype, None, field)
		if field_dt and field_dt != reference_doctype:
			agg_field_expr = f"`tab{field_dt}`.`{field_name}`"
		else:
			agg_field_expr = f"`tab{reference_doctype}`.`{field_name}`"

		rows = frappe.get_list(
			reference_doctype,
			filters=filters,
			or_filters=or_filters,
			fields=[f"{agg_fn}({agg_field_expr}) as result"],
			ignore_permissions=ignore_permissions,
			limit_page_length=0,
		)
		return (rows and rows[0].get("result")) or 0

	def _group_by(self, reference_doctype, config, context, action, ignore_permissions):
		"""Perform group_by aggregation via frappe.get_list with permission enforcement."""
		filters, or_filters = self._resolve_query_filters(
			config, context, action, reference_doctype=reference_doctype
		)
		aggregate_field = config.get("field", "name")
		group_field = config.get("group_by_field", aggregate_field)
		agg_function = config.get("agg_function", "count").lower()
		agg_field = config.get("agg_field", "name")
		safe_agg_fn = agg_function if agg_function in {"sum", "avg", "min", "max", "count"} else "count"

		group_dt, group_name = self._resolve_filter_doctype_and_field(reference_doctype, None, group_field)
		group_expr = (
			f"`tab{group_dt}`.`{group_name}`" if group_dt and group_dt != reference_doctype else group_name
		)

		agg_dt, agg_name = self._resolve_filter_doctype_and_field(reference_doctype, None, agg_field)
		agg_expr = (
			f"`tab{agg_dt}`.`{agg_name}`"
			if agg_dt and agg_dt != reference_doctype
			else f"`tab{reference_doctype}`.`{agg_name}`"
		)

		return frappe.get_list(
			reference_doctype,
			filters=filters,
			or_filters=or_filters,
			fields=[group_expr, f"{safe_agg_fn}({agg_expr}) as value"],
			group_by=group_expr,
			ignore_permissions=ignore_permissions,
			limit_page_length=0,
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

	def _resolve_filter_doctype_and_field(
		self, reference_doctype: str | None, doctype: str | None, fieldname: Any
	) -> tuple[str | None, str]:
		"""Resolve field path and DocType for filters.

		Translates child table fields (e.g. accounts.party_master) or table field references
		(doctype="accounts", fieldname="party_master") into Frappe's native child DocType format
		("Journal Entry Account", "party_master").
		"""
		if not fieldname:
			return doctype, ""

		fieldname_str = str(fieldname).strip()

		# Case 1: Dotted field syntax (e.g., accounts.party_master)
		if "." in fieldname_str:
			table_field, child_field = fieldname_str.split(".", 1)
			target_dt = doctype or reference_doctype
			if target_dt:
				try:
					meta = frappe.get_meta(target_dt)
					table_df = meta.get_field(table_field)
					if table_df and table_df.fieldtype in {"Table", "Table MultiSelect"} and table_df.options:
						return table_df.options, child_field
				except Exception:
					pass

		# Case 2: Doctype is specified as a table field name (e.g., doctype="accounts", fieldname="party_master")
		if doctype and reference_doctype and doctype != reference_doctype:
			try:
				meta = frappe.get_meta(reference_doctype)
				table_df = meta.get_field(doctype)
				if table_df and table_df.fieldtype in {"Table", "Table MultiSelect"} and table_df.options:
					return table_df.options, fieldname_str
			except Exception:
				pass

		# Case 3: Doctype is specified and is already a child table DocType or standard DocType
		if doctype:
			return doctype, fieldname_str

		return reference_doctype, fieldname_str

	def _resolve_query_filters(self, config, context, action=None, reference_doctype=None):
		"""Resolve and normalize both filters and or_filters with one shared path."""
		action_label = getattr(action, "label", None) or getattr(action, "action_id", None) or "Query Records"
		filters = self._resolve_filters_with_context(
			config.get("filters"), context, f"{action_label}.filters", action
		)
		filters = self._normalize_filters_for_backend(filters, reference_doctype=reference_doctype)
		or_filters = config.get("or_filters")
		if or_filters:
			or_filters = self._resolve_filters_with_context(
				or_filters, context, f"{action_label}.or_filters", action
			)
			or_filters = self._normalize_filters_for_backend(or_filters, reference_doctype=reference_doctype)
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

	def _is_canonical_filter_tree(self, value) -> bool:
		return isinstance(value, dict) and value.get("type") in {"group", "leaf"}

	def _resolve_fetch_filter_tree_values(self, node, context, path, action):
		"""Resolve FlexValues in canonical Fetch Records leaves without touching tree metadata."""
		if not isinstance(node, dict):
			return node
		node_type = node.get("type")
		if node_type == "group":
			resolved = dict(node)
			resolved["children"] = [
				self._resolve_fetch_filter_tree_values(child, context, f"{path}.children[{index}]", action)
				for index, child in enumerate(node.get("children") or [])
			]
			return resolved
		if node_type == "leaf":
			resolved = dict(node)
			if "value" in node:
				resolved["value"] = self._resolve_filter_leaf_value(
					node["value"], context, f"{path}.value", action
				)
			return resolved
		return node

	def _resolve_filter_leaf_value(self, value, context, path, action):
		"""Resolve a leaf's FlexValue payload while preserving raw JSON objects."""
		if isinstance(value, dict):
			if "mode" in value:
				return self._resolve_value_expression_with_context(value, context, path, action)
			return value
		if isinstance(value, str):
			return self._resolve_value_expression_with_context(value, context, path, action)
		return value

	def _canonical_fetch_filter_tree_to_backend(self, node, reference_doctype: str | None = None):
		"""Convert Fetch Records' canonical tree to native Query Builder filter tuples.

		Unlike the legacy-mode converter, this preserves dotted relationship paths
		and emits root-field tuples without a redundant DocType prefix. Frappe's
		Query Builder owns relationship resolution for this new mode.
		"""
		if not isinstance(node, dict):
			return node
		if node.get("type") == "leaf":
			field = node.get("field") or ""
			operator = node.get("operator") or "="
			value = self._extract_filter_value_payload(node.get("value"))
			operator, value = self._normalize_single_filter_operator(operator, value)
			return [field, operator, value]
		if node.get("type") == "group":
			operator = str(node.get("operator") or "and").lower()
			children = [
				self._canonical_fetch_filter_tree_to_backend(child, reference_doctype)
				for child in (node.get("children") or [])
			]
			children = [child for child in children if child not in (None, [])]
			if not children:
				return []
			if len(children) == 1:
				return children[0]
			# Frappe Query Builder treats a plain list of leaves as implicit AND.
			# Avoid explicit "and" tokens for flat groups so relationship paths can
			# be handled by QB's own filter parser instead of the compatibility shim.
			if operator == "and" and all(
				isinstance(child, list | tuple)
				and not any(isinstance(part, str) and part.casefold() in {"and", "or"} for part in child)
				and len(child) == 3
				for child in children
			):
				return children
			result = [children[0]]
			for child in children[1:]:
				result.extend([operator, child])
			return result
		return node

	def _canonical_filter_tree_to_backend(self, node, reference_doctype: str | None = None):
		"""Convert persisted QueryFilterTree data into native Frappe filter syntax."""
		if not isinstance(node, dict):
			return node
		if node.get("type") == "leaf":
			field = node.get("field") or ""
			doctype = node.get("doctype") or reference_doctype
			operator = node.get("operator") or "="
			value = self._extract_filter_value_payload(node.get("value"))
			# Canonical Fetch Records operators are case-insensitive; leave legacy
			# mode normalization untouched.
			if isinstance(operator, str):
				operator_key = operator.strip().casefold()
				if operator_key in {"starts with", "ends with"}:
					operator = operator_key
				elif operator_key == "timespan":
					operator = "Timespan"
			operator, value = self._normalize_single_filter_operator(operator, value)
			resolved_doctype, resolved_field = self._resolve_filter_doctype_and_field(
				reference_doctype, doctype, field
			)
			return [resolved_doctype or reference_doctype, resolved_field, operator, value]
		if node.get("type") == "group":
			operator = str(node.get("operator") or "and").lower()
			children = [
				self._canonical_filter_tree_to_backend(child, reference_doctype)
				for child in (node.get("children") or [])
			]
			children = [child for child in children if child not in (None, [])]
			if not children:
				return []
			if len(children) == 1:
				return children[0]
			result = [children[0]]
			for child in children[1:]:
				result.extend([operator, child])
			return result
		return node

	def _normalize_filters_for_backend(self, filters, reference_doctype: str | None = None):
		"""Recursively normalize filter operators and emit frappe-style filter tuples."""

		if self._is_canonical_filter_tree(filters):
			return self._canonical_filter_tree_to_backend(filters, reference_doctype)

		if isinstance(filters, dict):
			normalized = []
			for key, value in filters.items():
				dt_res, field_res = self._resolve_filter_doctype_and_field(reference_doctype, None, key)
				if isinstance(value, list) and len(value) == 2 and isinstance(value[0], str):
					op, val = self._normalize_single_filter_operator(value[0], value[1])
					if dt_res and dt_res != reference_doctype:
						normalized.append([dt_res, field_res, op, val])
					else:
						normalized.append([field_res, op, val])
				else:
					norm_val = self._normalize_filters_for_backend(value, reference_doctype=reference_doctype)
					if dt_res and dt_res != reference_doctype:
						normalized.append([dt_res, field_res, "=", norm_val])
					else:
						normalized.append([field_res, "=", norm_val])
			return normalized

		if isinstance(filters, list):
			normalized_list = []
			for item in filters:
				if isinstance(item, dict) and ("field" in item or "fieldname" in item):
					field_item = item.get("field") or item.get("fieldname")
					op_item = item.get("operator", "=")
					val_item = self._extract_filter_value_payload(item.get("value"))
					dt_item = item.get("doctype")
					op_item, val_item = self._normalize_single_filter_operator(op_item, val_item)
					dt_res, field_res = self._resolve_filter_doctype_and_field(
						reference_doctype, dt_item, field_item
					)
					if dt_res and dt_res != reference_doctype:
						normalized_list.append([dt_res, field_res, op_item, val_item])
					else:
						normalized_list.append([field_res, op_item, val_item])
					continue
				if isinstance(item, list):
					if len(item) == 4:
						dt_4, field_4, op_4, val_4 = item
						val_4 = self._extract_filter_value_payload(val_4)
						op_4, val_4 = self._normalize_single_filter_operator(op_4, val_4)
						resolved_dt, resolved_field = self._resolve_filter_doctype_and_field(
							reference_doctype, dt_4, field_4
						)
						if resolved_dt and resolved_dt != reference_doctype:
							normalized_list.append([resolved_dt, resolved_field, op_4, val_4])
						else:
							normalized_list.append([resolved_field, op_4, val_4])
						continue
					if (
						len(item) == 3
						and isinstance(item[0], str)
						and isinstance(item[1], str)
						and item[1].lower() not in ("and", "or")
					):
						field_3, op_3, val_3 = item
						val_3 = self._extract_filter_value_payload(val_3)
						op_3, val_3 = self._normalize_single_filter_operator(op_3, val_3)
						resolved_dt, resolved_field = self._resolve_filter_doctype_and_field(
							reference_doctype, None, field_3
						)
						if resolved_dt and resolved_dt != reference_doctype:
							normalized_list.append([resolved_dt, resolved_field, op_3, val_3])
						else:
							normalized_list.append([resolved_field, op_3, val_3])
						continue
				normalized_list.append(
					self._normalize_filters_for_backend(item, reference_doctype=reference_doctype)
				)
			return normalized_list

		return filters

	def _qualify_order_by(self, reference_doctype: str, order_by: str | None) -> str | None:
		"""Ensure order_by fields are table-qualified to prevent SQL ambiguity during child table joins."""
		if not order_by or not reference_doctype:
			return order_by

		parts = [p.strip() for p in str(order_by).split(",") if p.strip()]
		qualified_parts = []
		for part in parts:
			tokens = part.split()
			field_token = tokens[0]
			direction = f" {tokens[1]}" if len(tokens) > 1 else ""

			if "`" in field_token or "(" in field_token:
				qualified_parts.append(f"{field_token}{direction}")
				continue

			dt, field = self._resolve_filter_doctype_and_field(reference_doctype, None, field_token)
			target_dt = dt or reference_doctype
			qualified_parts.append(f"`tab{target_dt}`.`{field}`{direction}")

		return ", ".join(qualified_parts)

	def _query_list(self, reference_doctype, config, context, action, ignore_permissions):
		"""Execute frappe.get_list with configured filters, fields, etc."""
		filters, or_filters = self._resolve_query_filters(
			config, context, action, reference_doctype=reference_doctype
		)
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
		order_by = self._qualify_order_by(reference_doctype, order_by)
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
		if config.get("distinct"):
			kwargs["distinct"] = True
		if config.get("parent_doctype"):
			kwargs["parent_doctype"] = config["parent_doctype"]

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
			filters, or_filters = self._resolve_query_filters(
				config, context, action, reference_doctype=resolved_doctype
			)
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
		filters, or_filters = self._resolve_query_filters(
			config, context, action, reference_doctype=reference_doctype
		)

		rows = frappe.get_list(
			reference_doctype,
			filters=filters,
			or_filters=or_filters,
			fields=[f"`tab{reference_doctype}`.name"],
			limit_page_length=1,
			ignore_permissions=ignore_permissions,
		)
		return bool(rows)

	def _resolve_nested_primitive_value(self, val):
		"""Recursively strip all FlexValueControl configuration structures and resolve down to primitives."""
		if isinstance(val, dict):
			# Support standard FlexValueControl mode objects
			if "mode" in val:
				val = val.get("value")
				# If we stripped a dynamic wrapper, recursively evaluate the inner value
				return self._resolve_nested_primitive_value(val)
			else:
				resolved_dict = {}
				for k, v in val.items():
					res_v = self._resolve_nested_primitive_value(v)
					# Do not populate empty or unresolved configurations like {} or empty strings in dictionaries
					if res_v not in (None, "", {}, []):
						resolved_dict[k] = res_v
				return resolved_dict

		if isinstance(val, list):
			resolved_list = []
			for item in val:
				res_item = self._resolve_nested_primitive_value(item)
				if isinstance(res_item, list):
					resolved_list.extend(res_item)
				elif res_item not in (None, "", {}, []):
					resolved_list.append(res_item)
			return resolved_list

		return val

	def _query_report(self, reference_doctype, config, context, action, ignore_permissions):
		"""Run a report and return results as a list of dicts.

		Note: ignore_permissions is a no-op for Query Report mode.
		Frappe's query_report.run() enforces report-level permissions
		(frappe.has_permission(ref_doctype, "report")) internally and
		does not accept an ignore_permissions parameter. Report access
		for disallowed users will always raise PermissionError.
		"""
		report_name = config.get("report_name")
		if not report_name:
			frappe.throw(_("report_name is required in config for Query Report mode"))

		# Resolve filter variables but DO NOT normalize to list-of-lists.
		# Frappe's query_report.run() passes filters to frappe.db.sql(query, filters)
		# which expects a flat dict for %(key)s SQL parameter binding.
		action_label = getattr(action, "label", None) or getattr(action, "action_id", None) or "Query Records"
		raw_filters = config.get("filters") or {}
		resolved_filters = self._resolve_filters_with_context(
			raw_filters, context, f"{action_label}.filters", action
		)

		# Ensure filters remain a flat dict for SQL parameter binding.
		# If the resolved output is a list of UI-dict objects, convert to flat dict.
		report_filters = {}
		if isinstance(resolved_filters, dict):
			for k, v in resolved_filters.items():
				report_filters[k] = self._resolve_nested_primitive_value(v)
		elif isinstance(resolved_filters, list):
			# Convert list-of-dicts [{fieldname, operator, value}] to flat dict
			for item in resolved_filters:
				if isinstance(item, dict):
					field = item.get("field") or item.get("fieldname")
					val = self._resolve_nested_primitive_value(item.get("value"))
					if field:
						report_filters[field] = val
				elif isinstance(item, list) and len(item) >= 3:
					# [field, op, value] or [doctype, field, op, value]
					if len(item) == 4:
						report_filters[item[1]] = self._resolve_nested_primitive_value(item[3])
					else:
						report_filters[item[0]] = self._resolve_nested_primitive_value(item[2])

		# Native Frappe MultiSelectList compatibility: MultiSelectList filters must be serialized
		# as list of primitives (standard list of strings/integers/values) if of type array or list.
		for key, val in list(report_filters.items()):
			if isinstance(val, list):
				# Flatten list of lists if a sub-list is produced during resolution
				resolved_items = []
				for item in val:
					res_item = self._resolve_nested_primitive_value(item)
					if isinstance(res_item, list):
						resolved_items.extend(res_item)
					elif res_item not in (None, "", {}, []):
						resolved_items.append(res_item)
				report_filters[key] = resolved_items

		from frappe.desk.query_report import run as run_report

		result = run_report(
			report_name,
			filters=report_filters,
		)

		# Frappe's run() returns a dict with normalized "result" (list of dicts)
		# and "columns" (list of dicts) via its native normalize_result().
		return {
			"columns": result.get("columns", []) if isinstance(result, dict) else [],
			"result": result.get("result", []) if isinstance(result, dict) else [],
		}


# Register handler
HandlerRegistry.register(QueryRecordsHandler())
