# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

"""
Process Sync Module

Synchronizes Process docs from JSON files across all installed apps.
Modeled after frappe.model.sync for DocTypes.

During migrate:
1. Scans all {app}/{module}/process/{name}/{name}.json files
2. Creates/updates Process docs in the database
3. Populates operations from JSON metadata
"""

import json
import os
from pathlib import Path
from typing import Any, cast

import frappe
from frappe import _
from frappe.utils import get_datetime, update_progress_bar


def sync_all_processes():
	"""
	Sync Process docs from JSON files across all installed apps.
	Called from after_migrate hook.
	"""
	for app in frappe.get_installed_apps():
		sync_processes_for_app(app)


def sync_processes_for_app(app_name):
	"""
	Sync all Process docs for a given app.

	Scans {app}/{module}/process/{name}/{name}.json for all modules in the app.
	"""
	modules = frappe.get_all("Module Def", filters={"app_name": app_name}, pluck="name")
	if not modules:
		return

	process_files = []
	expected_process_names = set()

	for module_name in modules:
		try:
			module_path = frappe.get_module_path(module_name)
		except Exception:
			continue

		process_folder = Path(module_path) / "process"

		if not process_folder.exists():
			continue

		# Find all process directories
		for process_dir in process_folder.iterdir():
			if not process_dir.is_dir():
				continue

			json_file = process_dir / f"{process_dir.name}.json"
			if json_file.exists():
				process_files.append((json_file, module_name))
				expected_process_names.add(frappe.unscrub(process_dir.name))

	if not process_files:
		_prune_missing_standard_processes(modules, expected_process_names)
		return

	for i, (json_file, module_name) in enumerate(process_files):
		try:
			import_process_from_file(json_file, module_name)
		except Exception as e:
			frappe.log_error(f"Error syncing process from {json_file}: {e}", "Process Sync Error")

		update_progress_bar(f"Syncing Processes for {app_name}", i, len(process_files))

	_prune_missing_standard_processes(modules, expected_process_names)

	if process_files:
		print()  # New line after progress bar


def _prune_missing_standard_processes(module_names, expected_process_names):
	"""Remove file-backed standard Process docs whose JSON definition no longer exists."""
	if not module_names:
		return

	existing_processes = frappe.get_all(
		"Process",
		filters={
			"module": ["in", module_names],
			"is_standard": "Yes",
		},
		fields=["name", "module"],
	)

	for process in existing_processes:
		if process.name in expected_process_names:
			continue

		if get_process_json_path(process.name, process.module):
			continue

		try:
			frappe.delete_doc("Process", process.name, force=True, ignore_permissions=True)
		except Exception as exc:
			frappe.log_error(
				f"Error pruning missing process {process.name}: {exc}",
				"Process Sync Error",
			)


def import_process_from_file(json_path, module_name):
	"""
	Import a Process from a JSON file.

	Args:
	    json_path: Path to the {name}.json file
	    module_name: Module that contains this process
	"""
	with open(json_path) as f:
		data = json.load(f)

	process_name = data.get("process_name")
	if not process_name:
		return

	source_modified = _resolve_source_modified(data, json_path)

	# Check if module exists
	if not frappe.db.exists("Module Def", module_name):
		# Try to find module by scrubbed name
		module_name = frappe.unscrub(module_name)
		if not frappe.db.exists("Module Def", module_name):
			frappe.log_error(
				f"Module {module_name} not found for process {process_name}",
				"Process Sync Error",
			)
			return

	# Build operations from JSON metadata
	supported_operation_fields = _get_supported_process_operation_fields()
	operations = []
	for op in data.get("operations", []):
		action_overrides = _normalize_operation_contract_v2(process_name, op)
		op_row = {
			"func_name": op.get("func_name"),
			"label": op.get("label") or frappe.unscrub(op.get("func_name", "")),
			"enabled": op.get("enabled", 1),
			"visible_in_builder": op.get("visible_in_builder", 1),
			"icon": op.get("icon"),
			"color": op.get("color"),
			"requires_doc": op.get("requires_doc", 0),
			"can_stop_save": op.get("can_stop_save", 0),
			"is_terminal": op.get("is_terminal", 0),
			"writes_to": op.get("writes_to", "None"),
			"allows_async": op.get("allows_async", 0),
			"transactional": op.get("transactional", 0),
			"has_side_effect": op.get("has_side_effect", 0),
			"reads_vars": op.get("reads_vars"),
			"writes_vars": op.get("writes_vars"),
			"config_schema": op.get("config_schema"),
			"output_schema": op.get("output_schema"),
		}
		for optional_field in ("description", "for_doctype", "doctype_filters", "action_overrides"):
			if optional_field in supported_operation_fields:
				if optional_field == "action_overrides":
					op_row[optional_field] = action_overrides
				else:
					op_row[optional_field] = op.get(optional_field)

		operations.append(op_row)

	# Check if Process already exists
	# Check if Process already exists
	# Check if Process already exists
	if frappe.db.exists("Process", process_name):
		# Update existing
		doc = frappe.get_doc("Process", process_name)
		if not _should_sync_existing_process(doc, source_modified):
			return
		modified = False

		# Compare module names case-insensitively
		# DB might have "Ruleflow", JSON/Path might have "ruleflow"
		if doc.module != module_name and doc.module.lower() != module_name.lower():
			doc.module = module_name
			modified = True

		# Sync operations - update existing, add new
		existing_funcs = {op.func_name: op for op in doc.operations}
		incoming_funcs = {op.get("func_name") for op in operations if op.get("func_name")}

		for op_data in operations:
			func_name = op_data.get("func_name")
			if func_name in existing_funcs:
				# Update existing operation's metadata (sync all fields from JSON)
				existing = existing_funcs[func_name]

				# Update all fields from JSON to keep them in sync
				fields_to_update = [
					"label",
					"enabled",
					"visible_in_builder",
					"icon",
					"color",
					"requires_doc",
					"can_stop_save",
					"is_terminal",
					"writes_to",
					"allows_async",
					"transactional",
					"has_side_effect",
					"for_doctype",
					"doctype_filters",
					"reads_vars",
					"writes_vars",
					"config_schema",
					"output_schema",
				]
				for optional_field in ("description", "for_doctype", "doctype_filters", "action_overrides"):
					if optional_field in supported_operation_fields:
						fields_to_update.append(optional_field)

				op_modified = False
				for field in fields_to_update:
					json_value = op_data.get(field)
					current_value = getattr(existing, field, None)

					if current_value != json_value:
						setattr(existing, field, json_value)
						op_modified = True

				if op_modified:
					modified = True
			else:
				# Add new operation
				doc.append("operations", op_data)
				modified = True

		# Remove stale operations that no longer exist in the file-backed JSON definition
		for op in list(doc.operations):
			if op.func_name and op.func_name not in incoming_funcs:
				doc.remove(op)
				modified = True

		if modified:
			doc.flags.ignore_permissions = True
			doc.save()
	else:
		# Create new
		doc = frappe.new_doc("Process")
		doc.process_name = process_name
		doc.module = module_name

		for op_data in operations:
			doc.append("operations", op_data)

		doc.flags.ignore_permissions = True
		doc.insert()


def _resolve_source_modified(data: dict, json_path: str | os.PathLike) -> object | None:
	"""Resolve source modification datetime from JSON metadata."""
	modified_value = data.get("modified")
	if modified_value:
		try:
			return get_datetime(modified_value)
		except Exception:
			pass
	return None


def _should_sync_existing_process(doc, source_modified) -> bool:
	"""Sync only when source is newer than DB record."""
	if not source_modified:
		return True

	try:
		target_modified = get_datetime(doc.modified)
	except Exception:
		return True

	return source_modified >= target_modified


def _get_supported_process_operation_fields() -> set[str]:
	"""Return Process Operation fields that exist in both meta and DB columns."""
	meta = frappe.get_meta("Process Operation")
	supported = set()
	for fieldname in ("description", "for_doctype", "doctype_filters", "action_overrides"):
		if meta.has_field(fieldname) and frappe.db.has_column("Process Operation", fieldname):
			supported.add(fieldname)
	return supported


def _normalize_operation_contract_v2(process_name: str, operation_data: dict) -> str | None:
	"""Build/validate declarative contract_v2 payload inside action_overrides JSON."""
	func_name = operation_data.get("func_name")
	if not func_name:
		frappe.throw(_("Process '{0}' contains an operation without func_name").format(process_name))

	raw_overrides = operation_data.get("action_overrides")
	overrides = {}
	if isinstance(raw_overrides, dict):
		overrides = dict(raw_overrides)
	elif isinstance(raw_overrides, str) and raw_overrides.strip():
		try:
			parsed = json.loads(raw_overrides)
			if isinstance(parsed, dict):
				overrides = parsed
		except Exception:
			frappe.throw(
				_("Process operation '{0}.{1}' has invalid action_overrides JSON").format(
					process_name, func_name
				)
			)

	contract_v2 = overrides.get("contract_v2")
	if not isinstance(contract_v2, dict):
		frappe.throw(
			_("Process operation '{0}.{1}' must define action_overrides.contract_v2").format(
				process_name, func_name
			)
		)
	contract_v2_dict = cast(dict[str, Any], contract_v2)

	adapter_key = contract_v2_dict.get("adapter_key")
	if not adapter_key or not isinstance(adapter_key, str):
		frappe.throw(
			_("Process operation '{0}.{1}' must provide a valid string adapter_key").format(
				process_name, func_name
			)
		)

	for required_key in ("capabilities", "policy", "config_schema", "result_schema"):
		if required_key not in contract_v2_dict:
			frappe.throw(
				_("Process operation '{0}.{1}' contract_v2 is missing key '{2}'").format(
					process_name, func_name, required_key
				)
			)

	return json.dumps(overrides, separators=(",", ":"), sort_keys=True)


def get_process_json_path(process_name, module=None):
	"""
	Get the file path for a process's JSON file.

	Args:
	    process_name: Name of the process
	    module: Module name (optional, will be looked up if not provided)

	Returns:
	    Path object or None
	"""
	if not module:
		module = frappe.db.get_value("Process", process_name, "module")

	if not module:
		return None

	app = frappe.local.module_app.get(frappe.scrub(module))
	if not app:
		return None

	json_path = (
		Path(frappe.get_app_path(app))
		/ frappe.scrub(module)
		/ "process"
		/ frappe.scrub(process_name)
		/ f"{frappe.scrub(process_name)}.json"
	)

	return json_path if json_path.exists() else None
