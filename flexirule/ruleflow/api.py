# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

"""
Whitelisted API functions for FlexiRule Rule Engine
"""

import hashlib
import json
from typing import Any

import frappe
from frappe import _

from flexirule.ruleflow.core.compiler import ConditionCompiler
from flexirule.ruleflow.core.contracts import (
	get_contract_dto as _get_contract_dto,
)
from flexirule.ruleflow.core.contracts import (
	normalize_action_type,
)
from flexirule.ruleflow.core.permissions import require_builder_access
from flexirule.ruleflow.core.process_registry import (
	build_operation_registry,
	get_process_operation_policies,
	get_process_operation_registry_v2,
	get_process_registry,
)


def _require_api_access():
	"""Check if user has permission to use sensitive API endpoints.

	Delegates to the centralised ``require_builder_access`` so all
	FlexiRule modules share a single permission gate.
	"""
	require_builder_access()


def _build_error_response(
	exc: Exception,
	*,
	context: str = "FlexiRule API",
	extra: dict | None = None,
) -> dict[str, Any]:
	"""Build a structured error payload and log the traceback.

	Every API error response includes:
	- ``success``: always False
	- ``error_type``: the exception class name for programmatic handling
	- ``error``: the human-readable message
	- any additional keys from *extra*

	The full traceback is persisted via ``frappe.log_error`` so operators
	can perform forensic analysis from the Error Log DocType.
	"""
	frappe.log_error(
		title=f"{context}: {type(exc).__name__}",
		message=frappe.get_traceback(with_context=True),
	)
	response: dict[str, Any] = {
		"success": False,
		"error_type": type(exc).__name__,
		"error": str(exc),
	}
	if extra:
		response.update(extra)
	return response


# Layout fieldtypes to exclude by default
LAYOUT_FIELDTYPES = [
	"Tab Break",
	"Section Break",
	"Column Break",
	"HTML",
	"Fold",
	"Heading",
]

# System fields
SYSTEM_FIELDS = [
	{"value": "name", "label": "ID (name)", "fieldtype": "Data", "group": "System"},
	{
		"value": "owner",
		"label": "Created By (owner)",
		"fieldtype": "Link",
		"group": "System",
	},
	{
		"value": "creation",
		"label": "Created On (creation)",
		"fieldtype": "Datetime",
		"group": "System",
	},
	{
		"value": "modified",
		"label": "Modified On (modified)",
		"fieldtype": "Datetime",
		"group": "System",
	},
	{
		"value": "modified_by",
		"label": "Modified By (modified_by)",
		"fieldtype": "Link",
		"group": "System",
	},
	{
		"value": "docstatus",
		"label": "Document Status (docstatus)",
		"fieldtype": "Int",
		"group": "System",
	},
]


@frappe.whitelist()
def get_doctype_fields(doctype: str, filters: str | dict | None = None):
	"""
	Get fields for DocField autocomplete - grouped by parent/child tables

	Args:
	    doctype: DocType name
	    filters: JSON string with options:
	        - include_child_fields: bool (default: true)
	        - include_system_fields: bool (default: false)
	        - fieldtypes: list (whitelist specific types)
	        - exclude_fieldtypes: list (blacklist types)

	Returns:
	    dict: {
	        "parent_fields": [...],
	        "child_tables": [
	            {"table_name": "items", "doctype": "Sales Invoice Item", "fields": [...]}
	        ],
	        "system_fields": [...] if include_system_fields
	    }
	"""
	_require_api_access()
	if not doctype:
		return {"parent_fields": [], "child_tables": [], "system_fields": []}

	if not frappe.has_permission(doctype, "read"):
		frappe.throw(
			_("You do not have read permission for DocType {0}").format(doctype), frappe.PermissionError
		)

	# Parse filters
	if isinstance(filters, str):
		filters = json.loads(filters) if filters else {}
	elif filters is None:
		filters = {}

	include_child = filters.get("include_child_fields", True)
	include_system = filters.get("include_system_fields", False)
	allowed_types = filters.get("fieldtypes")
	excluded_types = filters.get("exclude_fieldtypes", LAYOUT_FIELDTYPES)

	# Get meta
	try:
		meta = frappe.get_meta(doctype)
	except Exception:
		return {"parent_fields": [], "child_tables": [], "system_fields": []}

	result: dict[str, list] = {"parent_fields": [], "child_tables": [], "system_fields": []}

	# Process parent fields
	for df in meta.fields:
		if should_include_field(df, allowed_types, excluded_types):
			result["parent_fields"].append(
				{
					"value": df.fieldname,
					"label": f"{df.label or df.fieldname}",
					"fieldtype": df.fieldtype,
					"options": df.options,
					"description": f"{df.fieldtype}" + (f" → {df.options}" if df.options else ""),
				}
			)

	# Process child tables
	if include_child:
		for df in meta.fields:
			if df.fieldtype == "Table" and df.options:
				child_fields = get_child_table_fields(df.options, df.fieldname, allowed_types, excluded_types)
				if child_fields:
					result["child_tables"].append(
						{
							"table_fieldname": df.fieldname,
							"table_label": df.label or df.fieldname,
							"child_doctype": df.options,
							"fields": child_fields,
						}
					)

	# Add system fields
	if include_system:
		result["system_fields"] = SYSTEM_FIELDS

	return result


def get_child_table_fields(child_doctype, table_fieldname, allowed_types=None, excluded_types=None):
	"""Get fields from a child table doctype"""
	try:
		meta = frappe.get_meta(child_doctype)
	except Exception:
		return []

	fields = []
	for df in meta.fields:
		if should_include_field(df, allowed_types, excluded_types):
			fields.append(
				{
					"value": f"{table_fieldname}.{df.fieldname}",
					"label": f"{df.label or df.fieldname}",
					"fieldtype": df.fieldtype,
					"options": df.options,
					"description": f"{df.fieldtype}" + (f" → {df.options}" if df.options else ""),
				}
			)

	return fields


def should_include_field(df, allowed_types=None, excluded_types=None):
	"""Check if field should be included based on filters"""
	# Check whitelist
	if allowed_types and df.fieldtype not in allowed_types:
		return False

	# Check blacklist
	if excluded_types and df.fieldtype in excluded_types:
		return False

	return True


@frappe.whitelist()
def test_rule(
	rule_name: str,
	doctype: str | None = None,
	docname: str | None = None,
	document_json: str | None = None,
	dry_run: int | bool | str = True,
	skip_log_enqueue: int | bool | str = True,
	save_log: int | bool | str | None = None,
	sim_user: str | None = None,
	sim_role: str | None = None,
):
	"""
	Test a rule against a document.
	Supports either an existing document (by docname) or a transient document (by document_json).
	"""
	_require_api_access()

	rule = frappe.get_doc("Rule", rule_name)

	if docname:
		doc = frappe.get_doc(doctype, docname)
	elif document_json:
		doc_data = json.loads(document_json)
		doc = frappe.get_doc(doc_data)
		# Transient docs might need to be 'local'
		doc.flags.ignore_permissions = True
	else:
		frappe.throw(_("Either docname or document_json must be provided"))

	from flexirule.ruleflow.core.coordinator import RuleCoordinator

	# Manual tests are a pre-activation validation stage and must also work for drafts/inactive rules.
	is_eligible, reason = RuleCoordinator.check_eligibility(
		rule,
		doc,
		event_name="Manual Test",
		skip_event_check=True,
		allow_inactive=True,
		context={"sim_user": sim_user, "sim_role": sim_role},
	)

	if not is_eligible:
		return {
			"success": False,
			"status": _("Skipped"),
			"message": _("Rule Skipped: {0}").format(reason),
			"execution": {
				"execution_id": None,
				"status": "Stopped",
				"duration": 0,
				"path_trace": [],
				"vars": {},
				"messages": [],
				"errors": [],
				"log_enqueued": False,
			},
			"path_trace": [],
			"vars": {},
		}

	try:
		from flexirule.ruleflow.core.engine import RuleEngine

		dry = bool(frappe.parse_json(dry_run))
		skip_enqueue = bool(frappe.parse_json(skip_log_enqueue))
		if save_log is not None and bool(frappe.parse_json(save_log)):
			dry = False
			skip_enqueue = False

		execution_context = {
			"doc": doc,
			"test_mode": True,
			"allow_inactive_rule_test": True,
			"dry_run": dry,
			"skip_log_enqueue": skip_enqueue,
			"sim_user": sim_user,
			"sim_role": sim_role,
		}
		RuleCoordinator.execute_rule(rule, context=execution_context, dry_run=dry)
		execution = getattr(frappe.local, "execution_payload", None) or {}
		if not execution:
			engine = RuleEngine(rule, execution_context=execution_context)
			engine.execute(doc, event_name="Manual Test")
			execution = engine.last_execution_payload or {
				"execution_id": engine.execution_id,
				"status": "Success",
				"duration": 0,
				"path_trace": getattr(engine, "path_trace", []),
				"vars": {},
				"messages": [],
				"errors": [],
				"log_enqueued": False,
			}

		# Include info about skipped trigger filters for transparency
		info_msg = _("Rule '{0}' executed successfully").format(rule.rule_name)
		if rule.compiled_expression:
			info_msg += " " + _("(trigger filters were bypassed for manual test)")

	except Exception as e:
		# The engine's ``finally`` block always writes the full execution
		# payload (including path_trace) to ``frappe.local.execution_payload``
		# even when the rule raises.  Prefer that over the local ``engine``
		# variable which only exists if we fell through to the manual
		# engine.execute() path.
		fallback_execution = (
			getattr(locals().get("engine"), "last_execution_payload", None)
			or getattr(frappe.local, "execution_payload", None)
			or {}
		)
		return _build_error_response(
			e,
			context="test_rule",
			extra={
				"status": _("Failed"),
				"execution": fallback_execution,
				"path_trace": fallback_execution.get("path_trace", []),
				"vars": fallback_execution.get("vars", {}),
				# Legacy compatibility for existing UI consumers
				"execution_path": fallback_execution.get("path_trace", []),
				"context_snapshot": fallback_execution.get("vars", {}),
			},
		)

	return {
		"success": True,
		"status": _(execution.get("status", "Success")),
		"execution": execution,
		"execution_id": execution.get("execution_id"),
		"path_trace": execution.get("path_trace", []),
		"vars": execution.get("vars", {}),
		# Legacy compatibility for existing UI consumers
		"execution_path": execution.get("path_trace", []),
		"context_snapshot": execution.get("vars", {}),
		"message": info_msg,
	}


@frappe.whitelist()
def execute_rule(
	rule_name: str,
	context: str | dict | None = None,
	dry_run: bool | str = True,
	skip_log_enqueue: bool | str = False,
):
	"""
	Pure execution API for a rule.
	"""
	_require_api_access()

	from flexirule.ruleflow.core.coordinator import RuleCoordinator

	ctx: dict | None = json.loads(context) if isinstance(context, str) else context

	dry: bool = bool(frappe.parse_json(dry_run))
	skip_enqueue: bool = bool(frappe.parse_json(skip_log_enqueue))
	if not isinstance(ctx, dict):
		ctx = {}
	ctx["skip_log_enqueue"] = skip_enqueue

	try:
		result = RuleCoordinator.execute_rule(rule_name, ctx, dry_run=dry)

		# Clean context for JSON serialization
		if isinstance(result, dict):
			result.pop("frappe", None)
			result.pop("doc", None)
			result.pop("old_doc", None)

		execution = getattr(frappe.local, "execution_payload", None) or {}
		return {
			"success": True,
			"status": execution.get("status", "Success"),
			"context": result,
			"execution": execution,
			"execution_id": execution.get("execution_id"),
			"path_trace": execution.get("path_trace", []),
			"vars": execution.get("vars", {}),
			"execution_log": getattr(frappe.local, "execution_log", []),
		}
	except Exception as e:
		execution = getattr(frappe.local, "execution_payload", None) or {}
		return _build_error_response(
			e,
			context="execute_rule",
			extra={
				"status": execution.get("status", "Failed"),
				"execution": execution,
				"path_trace": execution.get("path_trace", []),
				"vars": execution.get("vars", {}),
			},
		)


@frappe.whitelist()
def clear_cache(doctype: str | None = None):
	"""Clear rule cache"""
	_require_api_access()
	try:
		from flexirule.ruleflow.core.coordinator import RuleCoordinator

		RuleCoordinator.clear_cache(doctype)
		return {"success": True, "message": _("Cache cleared")}
	except Exception as e:
		return _build_error_response(e, context="clear_cache")


@frappe.whitelist()
def get_operator_config():
	"""
	Get fieldtype-to-operators mapping and operator labels for Condition Builder.
	Returns centralized config from ConditionCompiler.
	"""
	_require_api_access()
	return {
		"fieldtype_operators": ConditionCompiler.FIELDTYPE_OPERATORS,
		"operator_labels": ConditionCompiler.OPERATOR_LABELS,
	}


@frappe.whitelist()
def get_contract_dto():
	"""Return canonical action/trigger contracts for frontend consumers."""
	_require_api_access()
	contracts = _get_contract_dto()
	process_registry = get_process_registry(include_disabled=True, include_hidden=True)
	process_operation_policies = get_process_operation_policies(process_registry)
	process_operation_registry_v2 = get_process_operation_registry_v2(process_registry)
	operation_registry = build_operation_registry(process_registry, process_operation_policies)

	payload = {
		**contracts,
		"process_registry": process_registry,
		"operation_registry": operation_registry,
		"process_operation_registry_v2": process_operation_registry_v2,
	}
	payload["contract_version_hash"] = hashlib.sha256(
		json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
	).hexdigest()
	return payload


@frappe.whitelist()
def validate_rule_document(doc: str | dict, mode: str = "full"):
	"""Validate a rule payload and return structured errors/warnings.

	Args:
	    doc: Rule document (JSON string or dict)
	    mode: Validation mode — 'full' | 'draft' | 'node'
	        - 'full':  Complete validation for activation
	        - 'draft': Relaxed for building (skips activation checks)
	        - 'node':  Single-action validation
	"""
	_require_api_access()
	payload = json.loads(doc) if isinstance(doc, str) else (doc or {})

	from flexirule.ruleflow.core.validation_service import validate_rule_definition

	# Align API precheck with actual save pipeline:
	# compile trigger/action conditions before running validators.
	if isinstance(payload, dict):
		try:
			rule_payload = dict(payload)
			rule_payload.setdefault("doctype", "Rule")
			rule_doc = frappe.get_doc(rule_payload)
			if hasattr(rule_doc, "compile_conditions"):
				rule_doc.compile_conditions()
			return validate_rule_definition(rule_doc, mode=mode)
		except Exception:
			# Fallback to payload validation to preserve prior behavior if coercion fails.
			pass

	return validate_rule_definition(payload, mode=mode)


@frappe.whitelist()
def get_schema_field_options(
	schema_field: str | dict, parent_doctype: str, current_values: str | dict | None = None
):
	"""
	Get options for a schema field dynamically
	Used for dependent DocField sources
	"""
	_require_api_access()
	if not schema_field or not parent_doctype:
		return []

	field = json.loads(schema_field) if isinstance(schema_field, str) else schema_field
	current = json.loads(current_values) if isinstance(current_values, str) else (current_values or {})

	# Resolve options source
	options = field.get("options", "")

	if options == "parent.document_type":
		target_dt = parent_doctype
	elif options in current:
		target_dt = current[options]
	else:
		target_dt = options

	if not target_dt:
		return []

	return get_doctype_fields(target_dt, json.dumps(field.get("filters", {})))


@frappe.whitelist()
def get_rule_versions(rule_name: str, limit: int | str = 20):
	"""Get version history for a rule"""
	_require_api_access()
	from flexirule.ruleflow.doctype.rule.rule_version_hooks import (
		get_rule_versions as _get_versions,
	)

	return _get_versions(rule_name, int(limit))


@frappe.whitelist()
def restore_rule_version(rule_name: str, version_name: str):
	"""Restore a rule to a previous version"""
	_require_api_access()
	from flexirule.ruleflow.doctype.rule.rule_version_hooks import (
		restore_rule_version as _restore,
	)

	return _restore(rule_name, version_name)


@frappe.whitelist()
def export_rule(rule_name: str):
	"""Export a rule to JSON"""
	_require_api_access()
	from flexirule.ruleflow.utils.import_export import export_rule as _export

	return _export(rule_name)


@frappe.whitelist()
def import_rule(import_data: str | dict, overwrite: bool | str = False):
	"""Import a rule from JSON"""
	_require_api_access()
	from flexirule.ruleflow.utils.import_export import import_rule as _import

	overwrite = frappe.parse_json(overwrite) if isinstance(overwrite, str) else overwrite
	return _import(import_data, overwrite)


@frappe.whitelist()
def get_action_context_schema(rule_name: str, action_id: str):
	"""
	Get available context variables for a specific action in rule flow.
	Used by UI to enable context-aware field selection.
	"""
	_require_api_access()
	rule = frappe.get_doc("Rule", rule_name)
	if not frappe.has_permission("Rule", "read", doc=rule):
		frappe.throw(
			_("You do not have permission to read Rule {0}").format(rule_name), frappe.PermissionError
		)

	result: dict[str, list] = {"doc_fields": [], "predecessor_outputs": []}

	# Get doc fields
	try:
		fields_data = get_doctype_fields(rule.document_type)
		result["doc_fields"] = fields_data.get("parent_fields", [])
	except Exception:
		pass

	# Build action maps
	action_map = {}
	for a in rule.actions:
		key = a.action_id or a.name
		action_map[key] = a

	# Find predecessors by traversing graph backwards
	predecessors = set()
	queue = [action_id]
	visited: set[str] = set()

	while queue:
		current_id = queue.pop(0)
		if current_id in visited:
			continue
		visited.add(current_id)

		for action in rule.actions:
			action_key = action.action_id or action.name
			if action.next_step_if_true == current_id or action.next_step_if_false == current_id:
				predecessors.add(action_key)
				queue.append(action_key)

	# Get output schemas for predecessors
	for pred_id in predecessors:
		action = action_map.get(pred_id)
		if not action or not action.process_name:
			continue

		output_schema = None
		try:
			process_doc = frappe.get_cached_doc("Process", action.process_name)
			operation_doc = process_doc.get_operation(action.operation)
			if operation_doc and operation_doc.output_schema:
				import json

				output_schema = json.loads(operation_doc.output_schema)
		except Exception:
			pass

		result["predecessor_outputs"].append(
			{
				"action_id": action.action_id or action.name,
				"action_label": action.action_label,
				"return_variable": action.return_variable,
				"output_schema": output_schema,
			}
		)

	return result


@frappe.whitelist()
def get_process_operations(process_name: str):
	"""
	Get enabled operations for a specific process as normalized DTOs.
	Returns stable shape for both Rule Form and Rule Builder consumers.
	"""
	_require_api_access()
	if not process_name:
		return []

	rows = frappe.get_all(
		"Process Operation",
		filters={
			"parenttype": "Process",
			"parent": process_name,
			"enabled": 1,
		},
		fields=[
			"func_name",
			"label",
			"description",
			"enabled",
			"visible_in_builder",
			"icon",
			"color",
			"writes_to",
			"is_terminal",
			"requires_doc",
			"can_stop_save",
			"allows_async",
			"transactional",
			"for_doctype",
			"doctype_filters",
			"reads_vars",
			"writes_vars",
			"config_schema",
			"output_schema",
			"action_overrides",
		],
		order_by="idx asc",
	)

	# Stable DTO with compatibility fields
	result = []
	for r in rows:
		if not r.get("func_name"):
			continue
		from flexirule.ruleflow.core.process_contract_v2 import resolve_process_operation_contract_v2

		contract_v2 = resolve_process_operation_contract_v2(
			process_name,
			r.get("func_name"),
			r,
			strict=True,
		)

		result.append(
			{
				"value": r.get("func_name"),
				"func_name": r.get("func_name"),
				"label": r.get("label") or r.get("func_name"),
				"description": r.get("description") or "",
				"enabled": r.get("enabled", 1),
				"visible_in_builder": r.get("visible_in_builder", 1),
				"icon": r.get("icon"),
				"color": r.get("color"),
				"writes_to": r.get("writes_to"),
				"is_terminal": r.get("is_terminal", 0),
				"requires_doc": r.get("requires_doc", 0),
				"can_stop_save": r.get("can_stop_save", 0),
				"allows_async": r.get("allows_async", 0),
				"transactional": r.get("transactional", 0),
				"for_doctype": r.get("for_doctype"),
				"doctype_filters": r.get("doctype_filters"),
				"reads_vars": r.get("reads_vars"),
				"writes_vars": r.get("writes_vars"),
				"config_schema": contract_v2.get("config_schema"),
				"output_schema": contract_v2.get("result_schema"),
				"action_overrides": r.get("action_overrides"),
				"operation_key": contract_v2.get("operation_key"),
				"adapter_key": contract_v2.get("adapter_key"),
				"capabilities": contract_v2.get("capabilities"),
				"policy": contract_v2.get("policy"),
				"result_schema": contract_v2.get("result_schema"),
				"ui_schema": (contract_v2.get("config_schema") or {}).get("ui_schema"),
			}
		)

	return result


@frappe.whitelist()
def get_all_process_operations():
	"""Return all enabled Process operations across all apps for fuzzy search."""
	_require_api_access()
	processes = frappe.get_all("Process", fields=["name", "module"])
	results = []
	for p in processes:
		ops = frappe.get_all(
			"Process Operation",
			filters={"parent": p.name, "parenttype": "Process", "enabled": 1, "visible_in_builder": 1},
			fields=["func_name", "label", "description"],
			order_by="idx asc",
		)
		for op in ops:
			results.append(
				{
					"process": p.name,
					"module": p.module,
					"operation": op.func_name,
					"label": op.label or op.func_name,
					"description": op.description or "",
				}
			)
	return results


@frappe.whitelist()
def clone_rule(rule_name: str, new_name: str | None = None):
	"""
	Clone a rule to create a new version or copy.
	Resets status to Draft (inactive) and clears execution stats.
	"""
	_require_api_access()
	try:
		doc = frappe.get_doc("Rule", rule_name)

		# Use Frappe's copy mechanism
		new_doc = frappe.copy_doc(doc)
		new_doc.is_active = 0
		new_doc.status = "Draft"
		new_doc.last_error = None

		if new_name:
			new_doc.rule_name = new_name

		# If no new name provided, Frappe often appends a number if naming is set,
		# but Rule uses "field:rule_name". We might need to ensure uniqueness if logic requires.
		# However, copy_doc usually clears the name if it's set to autoname.
		# But here autoname="field:rule_name".
		if not new_name:
			new_doc.rule_name = f"{doc.rule_name} (Copy)"

		new_doc.insert()
		return new_doc.name

	except Exception as e:
		frappe.log_error("Rule Clone Failed")
		frappe.throw(_("Failed to clone rule: {0}").format(str(e)))


@frappe.whitelist()
def amend_rule(rule_name: str) -> str:
	"""
	Create a new version (amendment) of a rule.

	The original rule stays active. The copy becomes a draft amendment
	with incremented version and a link back via `previous_rule`.

	Returns:
	    Name of the new amended rule.
	"""
	_require_api_access()
	from flexirule.ruleflow.core.rule_service import amend_rule as _amend_rule

	return _amend_rule(rule_name)


@frappe.whitelist()
def test_action_query(
	rule_name: str,
	action_id: str,
	context_doc: str | dict[str, Any] | None = None,
	overrides: str | dict[str, Any] | None = None,
) -> dict[str, Any]:
	"""
	Execute a single action in isolation for testing.
	Returns detected return fields for auto-populating returns_keys.
	"""
	_require_api_access()
	rule = frappe.get_doc("Rule", rule_name)

	# Find the action
	action = None
	for a in rule.actions:
		if a.action_id == action_id:
			action = a
			break

	if not action:
		frappe.throw(_("Action {0} not found in rule {1}").format(action_id, rule_name))
		raise ValueError("Action not found")

	# Apply overrides if provided (useful for testing UI changes without saving)
	if overrides:
		overrides_dict: dict = json.loads(overrides) if isinstance(overrides, str) else overrides
		for key, val in overrides_dict.items():
			# Config and mapping fields might be strings in DB but dicts/lists in overrides
			json_fields = [
				"config",
				"condition_json",
				"resolved_output_schema",
			]
			if key in json_fields and not isinstance(val, str | bytes):
				setattr(action, key, json.dumps(val))
			elif hasattr(action, key):
				if key == "config" and isinstance(val, dict):
					setattr(action, key, json.dumps(val))
				else:
					setattr(action, key, val)

	# Build a minimal context
	doc = None
	if context_doc:
		import json as json_mod

		doc_data = json_mod.loads(context_doc) if isinstance(context_doc, str) else context_doc
		doc = frappe.get_doc(doc_data)
	elif rule.document_type:
		# Try to get a recent document for testing
		recent = frappe.get_all(rule.document_type, limit=1, pluck="name")
		if recent:
			doc = frappe.get_doc(rule.document_type, recent[0])

	if not doc:
		frappe.throw(_("No document available for testing. Provide context_doc."))

	from flexirule.ruleflow.core.engine import RuleEngine

	engine = RuleEngine(rule, {"test_mode": True})
	context = engine._initialize_context(doc)

	# Execute only this one action via handler
	from flexirule.ruleflow.core.action_handlers import HandlerRegistry

	handler = HandlerRegistry.get(normalize_action_type(action.action_type))
	if not handler:
		frappe.throw(_("No handler for action type: {0}").format(action.action_type))
		raise ValueError("Handler not found")

	# Re-assert for mypy since throw is not always detected as terminal
	if handler is None:
		return {"success": False, "error": "Handler not found", "result": None, "schema": [], "duration": 0}

	import time

	start = time.time()
	schema = []
	result = None
	duration = 0.0

	# 1. Pre-detection from Action Config (most reliable for Query List/Doc/Count)
	# This ensures we get a schema even if the execution fails due to missing data/context
	if action and action.action_type == "Query Records":
		try:
			config_data: dict = (
				json.loads(action.config) if isinstance(action.config, str) else (action.config or {})
			)
			if config_data is None:
				config_data = {}

			mode = (action.operation or config_data.get("operation")) if action else None
			reference_doctype = action.reference_doctype if action else None

			if (mode == "Query List" or mode == "Query Doc") and reference_doctype:
				fields = config_data.get("fields") or (["name"] if mode == "Query List" else [])
				meta = frappe.get_meta(reference_doctype)
				system_fields = {f["value"]: f for f in SYSTEM_FIELDS}

				if mode == "Query Doc" and not fields:
					# For Query Doc, if no fields specified, we return all non-no_value fields
					for df in meta.fields:
						if df.fieldtype not in frappe.model.no_value_fields:
							schema.append(
								{
									"fieldname": df.fieldname,
									"label": df.label,
									"fieldtype": df.fieldtype,
									"options": df.options,
									"mandatory": df.reqd,
								}
							)
					# Add system fields
					for sf in SYSTEM_FIELDS:
						schema.append(
							{
								"fieldname": sf["value"],
								"label": sf["label"],
								"fieldtype": sf.get("fieldtype", "Data"),
								"options": sf.get("options"),
								"mandatory": 0,
							}
						)
				else:
					for f in fields:
						df = None
						label = f
						if "." in f:
							table_fn, field_fn = f.split(".", 1)
							table_df = meta.get_field(table_fn)
							if table_df and table_df.fieldtype in ["Table", "Table MultiSelect"]:
								child_meta = frappe.get_meta(table_df.options)
								df = child_meta.get_field(field_fn)
								if not df and field_fn in system_fields:
									df = frappe._dict(system_fields[field_fn])

								if df:
									label = f"{table_df.label}: {df.label or df.fieldname}"
						else:
							df = meta.get_field(f)
							if not df and f in system_fields:
								df = frappe._dict(system_fields[f])

							if df:
								label = df.label or df.fieldname

						schema.append(
							{
								"fieldname": f,
								"label": label,
								"fieldtype": df.fieldtype if df else "Data",
								"options": df.options if df else None,
								"mandatory": df.reqd if df and hasattr(df, "reqd") else 0,
							}
						)
			elif mode in ["Count", "Sum", "Average", "Min", "Max"]:
				label_map = {
					"Count": _("Count Result"),
					"Sum": _("Sum Result"),
					"Average": _("Average Result"),
					"Min": _("Min Result"),
					"Max": _("Max Result"),
				}
				schema.append(
					{
						"fieldname": "result",
						"label": label_map.get(mode, _("Query Result")),
						"fieldtype": "Float" if mode == "Average" else "Int",
						"options": None,
						"mandatory": 0,
					}
				)
		except Exception:
			pass

	try:
		result, _next_id = handler.execute(action, context, engine)
		# Apply post-processing (output mapping, return validation, mutation)
		engine._post_process_action_result(action, result, context)
		duration = time.time() - start

		# 2. Refine detection from result if execution succeeded
		if action and action.action_type == "Query Records":
			try:
				config_data2: dict = (
					json.loads(action.config) if isinstance(action.config, str) else (action.config or {})
				)
				mode = (action.operation or config_data2.get("operation")) if action else None

				if mode == "Query Report" and isinstance(result, dict) and "columns" in result:
					# Reports MUST be detected from result since columns are dynamic
					report_schema = []
					columns = result.get("columns") or []
					for c in columns:
						if isinstance(c, dict):
							report_schema.append(
								{
									"fieldname": c.get("fieldname") or c.get("label"),
									"label": c.get("label") or c.get("fieldname"),
									"fieldtype": c.get("fieldtype") or "Data",
									"options": c.get("options"),
									"mandatory": c.get("mandatory", 0),
								}
							)
						elif isinstance(c, str):
							report_schema.append(
								{
									"fieldname": c,
									"label": c,
									"fieldtype": "Data",
									"options": None,
									"mandatory": 0,
								}
							)
					if report_schema:
						schema = report_schema
			except Exception:
				pass

		# 3. Fallback to result inspection if still empty
		if not schema:
			if isinstance(result, dict):
				for k in result.keys():
					schema.append(
						{"fieldname": k, "label": k, "fieldtype": "Data", "options": None, "mandatory": 0}
					)
			elif isinstance(result, list) and result and isinstance(result[0], dict):
				for k in result[0].keys():
					schema.append(
						{"fieldname": k, "label": k, "fieldtype": "Data", "options": None, "mandatory": 0}
					)

		return {
			"success": True,
			"result": result,
			"schema": schema,
			"duration": round(duration, 4),
		}
	except Exception as e:
		# Even if execution failed, we return the metadata-based schema if we found one
		if schema:
			return {
				"success": False,
				"error": str(e),
				"result": None,
				"schema": schema,
				"duration": round(time.time() - start, 4),
			}
		return _build_error_response(e, context="test_action_query")


@frappe.whitelist()
def get_rule_stats(rule_name: str):
	"""Compute rule execution stats dynamically from Rule Execution Log"""
	_require_api_access()

	stats = frappe.db.sql(
		"""
		SELECT
			COUNT(*) as execution_count,
			AVG(duration) as avg_execution_time,
			MAX(creation) as last_executed,
			SUM(CASE WHEN status = 'Success' THEN 1 ELSE 0 END) as success_count
		FROM `tabRule Execution Log`
		WHERE rule = %s
		""",
		(rule_name,),
		as_dict=True,
	)

	if not stats or not stats[0].execution_count:
		return {"execution_count": 0, "avg_execution_time": 0.0, "success_rate": 0.0, "last_executed": None}

	result = stats[0]
	execution_count = result.execution_count or 0
	success_count = result.success_count or 0

	success_rate = (success_count / execution_count * 100.0) if execution_count > 0 else 0.0

	return {
		"execution_count": execution_count,
		"avg_execution_time": result.avg_execution_time or 0.0,
		"success_rate": success_rate,
		"last_executed": result.last_executed,
	}


# ═══════════════════════════════════════════════════════════════
# Phase 2: Lifecycle & Testing APIs
# ═══════════════════════════════════════════════════════════════


@frappe.whitelist()
def transition_rule(rule_name: str, target_status: str):
	"""Transition a rule to a new status."""
	_require_api_access()

	rule = frappe.get_doc("Rule", rule_name)
	if target_status not in ["Draft", "Active", "Disabled", "Invalid", "Error", "Archived"]:
		frappe.throw(_("Invalid target status: {0}").format(target_status))

	if target_status == "Active":
		from flexirule.ruleflow.core.validation_service import validate_rule_definition

		rule.is_active = 1
		result = validate_rule_definition(rule, mode="full")
		if not result["valid"]:
			rule.is_active = 0
			frappe.throw(
				_("Cannot activate rule. Validation errors:") + "<br>" + "<br>".join(result["errors"]),
				frappe.ValidationError,
			)

	rule.status = target_status
	rule.is_active = 1 if target_status == "Active" else 0
	rule.save(ignore_permissions=True)

	frappe.clear_document_cache("Rule", rule.name)
	frappe.clear_cache(doctype="Rule")

	return {
		"status": rule.status,
		"is_active": rule.is_active,
		"message": _("Rule transitioned to {0}").format(target_status),
	}


@frappe.whitelist()
def get_allowed_transitions(rule_name: str):
	"""Get allowed lifecycle transitions for a rule's current status."""
	_require_api_access()

	rule = frappe.get_doc("Rule", rule_name)
	current_status = rule.status or "Draft"

	transitions = []
	if current_status == "Draft":
		transitions.append({"target": "Active", "label": str(_("Activate")), "key": "activate"})
		transitions.append({"target": "Archived", "label": str(_("Archive")), "key": "archive"})
	elif current_status == "Active":
		transitions.append({"target": "Draft", "label": str(_("Unlock for Editing")), "key": "deactivate"})
		transitions.append({"target": "Disabled", "label": str(_("Disable")), "key": "disable"})
		transitions.append({"target": "Archived", "label": str(_("Archive")), "key": "archive"})
	elif current_status == "Disabled":
		transitions.append({"target": "Active", "label": str(_("Activate")), "key": "activate"})
		transitions.append({"target": "Draft", "label": str(_("Unlock for Editing")), "key": "deactivate"})
	elif current_status == "Archived":
		transitions.append({"target": "Draft", "label": str(_("Restore as Draft")), "key": "restore"})

	return transitions


@frappe.whitelist()
def validate_node(rule_name: str, action_id: str):
	"""Validate a single node/action in isolation.

	Called by the config modal's "Save" button to check one action
	against its contract + handler without running full rule validation.

	Args:
	    rule_name: Rule document name
	    action_id: The action_id of the node to validate

	Returns:
	    dict: {"valid": bool, "errors": [], "warnings": [], "mode": "node"}
	"""
	_require_api_access()

	from flexirule.ruleflow.core.validation_service import validate_single_action

	return validate_single_action(rule_name, action_id)


@frappe.whitelist()
def simulate_rule(
	rule_name: str,
	doctype: str | None = None,
	docname: str | None = None,
	test_context: str | dict | None = None,
):
	"""Simulate rule execution without side effects.

	Runs the rule engine in dry-run + test mode for a given document,
	returning the execution path and variable state at each step.

	Args:
	    rule_name: Rule document name
	    doctype: Target document type (optional, inferred from rule)
	    docname: Target document name
	    test_context: Optional JSON context variables

	Returns:
	    dict: {
	        "success": bool,
	        "path_trace": [...],
	        "vars": {...},
	        "step_details": [...],
	        "message": str
	    }
	"""
	_require_api_access()

	rule = frappe.get_doc("Rule", rule_name)
	doctype = doctype or rule.document_type

	if not docname:
		frappe.throw(_("Document name (docname) is required for simulation"))

	doc = frappe.get_doc(doctype, docname)

	from flexirule.ruleflow.core.engine import RuleEngine

	try:
		engine = RuleEngine(
			rule,
			{
				"test_mode": True,
				"dry_run": True,
				"skip_log_enqueue": True,
				"simulation": True,
			},
		)
		engine.execute(doc, event_name="Simulation")
		execution = engine.last_execution_payload or {
			"execution_id": engine.execution_id,
			"status": "Success",
			"duration": 0,
			"path_trace": getattr(engine, "path_trace", []),
			"vars": {},
			"messages": [],
			"errors": [],
		}

		return {
			"success": True,
			"status": execution.get("status", "Success"),
			"path_trace": execution.get("path_trace", []),
			"vars": execution.get("vars", {}),
			"step_details": execution.get("step_details", []),
			"duration": execution.get("duration", 0),
			"message": _("Simulation completed successfully"),
		}
	except Exception as e:
		fallback = getattr(locals().get("engine"), "last_execution_payload", None) or {}
		return _build_error_response(
			e,
			context="simulate_rule",
			extra={
				"status": "Failed",
				"path_trace": fallback.get("path_trace", []),
				"vars": fallback.get("vars", {}),
				"step_details": [],
				"message": _("Simulation failed: {0}").format(str(e)),
			},
		)


@frappe.whitelist()
def get_execution_preview(rule_name: str, docname: str):
	"""Preview which path a rule would take for a given document.

	This is a lightweight check that evaluates conditions without executing
	any action handlers. Useful for "what would happen?" previews.

	Args:
	    rule_name: Rule document name
	    docname: Target document name

	Returns:
	    dict: {
	        "eligible": bool,
	        "reason": str,
	        "predicted_path": [action_id, ...],
	        "skipped_actions": [action_id, ...]
	    }
	"""
	_require_api_access()

	rule = frappe.get_doc("Rule", rule_name)
	doc = frappe.get_doc(rule.document_type, docname)

	from flexirule.ruleflow.core.coordinator import RuleCoordinator

	# Check eligibility first
	is_eligible, reason = RuleCoordinator.check_eligibility(
		rule, doc, event_name="Preview", skip_event_check=True
	)

	if not is_eligible:
		return {
			"eligible": False,
			"reason": reason,
			"predicted_path": [],
			"skipped_actions": [],
		}

	# Walk the graph evaluating conditions to predict the path
	predicted_path = []
	skipped_actions = []
	actions_by_id = {a.action_id: a for a in (rule.actions or [])}

	# Start from the entry action
	current_id = None
	for action in rule.actions or []:
		if action.action_type == "Entry Action" or action.action_id == "root":
			current_id = action.action_id
			break

	visited: set[str] = set()
	max_steps = 100  # Safety limit

	while current_id and current_id not in visited and len(visited) < max_steps:
		visited.add(current_id)
		action = actions_by_id.get(current_id)
		if not action:
			break

		predicted_path.append(current_id)

		# Check if disabled
		if not action.is_enabled:
			skipped_actions.append(current_id)
			break

		# Terminal actions
		contract = None
		try:
			from flexirule.ruleflow.core.contracts import get_contract

			contract = get_contract(normalize_action_type(action.action_type))
		except Exception:
			pass

		if contract and contract.get("terminal"):
			break

		# For conditions, try to evaluate which branch
		if action.action_type == "Condition" and action.compiled_expression:
			try:
				from flexirule.ruleflow.core.evaluator import evaluate_condition

				result = evaluate_condition(
					action.compiled_expression, {"doc": doc, "old_doc": None, "frappe": frappe}
				)
				current_id = action.next_step_if_true if result else action.next_step_if_false
			except Exception:
				# If evaluation fails, follow the true path
				current_id = action.next_step_if_true
		else:
			current_id = action.next_step_if_true

	return {
		"eligible": True,
		"reason": _("Rule is eligible"),
		"predicted_path": predicted_path,
		"skipped_actions": skipped_actions,
	}


# ═══════════════════════════════════════════════════════════════
# Phase 4: Backend Alignment APIs
# ═══════════════════════════════════════════════════════════════


@frappe.whitelist()
def initialize_rule_graph(rule_name: str):
	"""Ensure a rule has a valid Trigger → End graph structure.

	Called on new Rule creation or when resetting a rule's graph.
	If the rule already has actions/visual_data, this is a no-op.

	Args:
	    rule_name: Rule document name

	Returns:
	    dict: {"initialized": bool, "rule": {...}}
	"""
	_require_api_access()

	from flexirule.ruleflow.core.graph_service import ensure_default_graph

	rule = frappe.get_doc("Rule", rule_name)
	initialized = ensure_default_graph(rule)

	if initialized:
		rule.save(ignore_permissions=True)

	return {
		"initialized": initialized,
		"rule": rule.as_dict(),
	}


@frappe.whitelist()
def get_node_config_schema(
	action_type: str,
	operation: str | None = None,
	process_name: str | None = None,
):
	"""Return the full field schema for configuring a node.

	Merges DocType metadata (Rule Action fields) with contract overrides
	to generate a complete, dynamic config form schema. Used by the
	frontend to render node config forms without hardcoded field lists.

	Args:
	    action_type: Action type (e.g., "Process", "Condition")
	    operation: Optional operation name
	    process_name: Optional process name

	Returns:
	    dict: {
	        "fields": [...],
	        "contract": {...},
	        "policy": {...},
	        "sections": [...]
	    }
	"""
	_require_api_access()

	from flexirule.ruleflow.core.graph_service import (
		get_node_config_schema as _get_schema,
	)

	return _get_schema(action_type, operation=operation, process_name=process_name)


@frappe.whitelist()
def search_actions(query: str = "", filters: str | dict | None = None, limit: int | str = 20):
	"""Fuzzy search across all available action types and operations.

	Used by the ActionSelector node to provide a searchable list
	of available actions, organized by category.

	Args:
	    query: Search query string
	    filters: Optional JSON filters
	    limit: Max results (default 20)

	Returns:
	    list: [{
	        "action_type": str,
	        "operation": str|null,
	        "process_name": str|null,
	        "label": str,
	        "description": str,
	        "icon": str,
	        "color": str,
	        "category": str,
	        "score": float
	    }, ...]
	"""
	_require_api_access()

	from flexirule.ruleflow.core.search_service import search_actions as _search

	parsed_filters: dict | None = None
	if isinstance(filters, str):
		parsed_filters = json.loads(filters)
	elif isinstance(filters, dict):
		parsed_filters = filters
	elif filters is not None:
		frappe.throw(_("filters must be dict or json string"))

	return _search(query, filters=parsed_filters, limit=int(limit))
