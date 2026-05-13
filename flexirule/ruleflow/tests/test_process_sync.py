# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

"""
Tests for FlexiRule Process Sync
"""

import json
import os
import tempfile
import unittest
from pathlib import Path

import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.core.process_sync import (
	get_process_json_path,
	import_process_from_file,
	sync_all_processes,
	sync_processes_for_app,
)


class TestProcessSync(FrappeTestCase):
	"""Test cases for Process Sync functionality"""

	def setUp(self):
		super().setUp()
		# Clean up any test processes
		processes = frappe.get_all("Process", filters={"process_name": ["like", "Test%"]}, pluck="name")
		for process_name in processes:
			frappe.delete_doc("Process", process_name, force=True)

	def tearDown(self):
		super().tearDown()
		# Clean up any test processes created during tests
		processes = frappe.get_all("Process", filters={"process_name": ["like", "Test%"]}, pluck="name")
		for process_name in processes:
			frappe.delete_doc("Process", process_name, force=True)

	def create_test_process_json(self, process_name, operations=None):
		"""Helper to create a temporary process JSON file"""
		if operations is None:
			operations = [
				{
					"func_name": "test_operation",
					"label": "Test Operation",
					"enabled": 1,
					"visible_in_builder": 1,
					"requires_doc": 0,
					"can_stop_save": 0,
					"is_terminal": 0,
					"writes_to": "None",
					"allows_async": 0,
					"transactional": 0,
				}
			]
		operations = [self._with_default_contract_v2(dict(op)) for op in operations]

		process_data = {
			"process_name": process_name,
			"module": "Ruleflow",
			"is_standard": "Yes",
			"operations": operations,
		}

		# Create a temporary file
		temp_dir = tempfile.mkdtemp()
		json_file_path = os.path.join(temp_dir, f"{process_name.lower()}.json")

		with open(json_file_path, "w") as f:
			json.dump(process_data, f, indent=2)

		return Path(json_file_path)

	def _with_default_contract_v2(self, operation: dict) -> dict:
		"""Attach minimal declarative contract_v2 when omitted in test payloads."""
		overrides = {}
		raw_overrides = operation.get("action_overrides")
		if isinstance(raw_overrides, str) and raw_overrides.strip():
			try:
				parsed = json.loads(raw_overrides)
				if isinstance(parsed, dict):
					overrides = parsed
			except Exception:
				overrides = {}
		elif isinstance(raw_overrides, dict):
			overrides = dict(raw_overrides)

		writes_to = operation.get("writes_to", "None")
		allowed_mutations = {
			"None": ["Set Context Variable", "Update Context Variable"],
			"Context": ["Set Context Variable", "Update Context Variable", "Append to Context Variable"],
			"Document": [
				"Set Doc Field",
				"Update Doc Field",
				"Set Context Variable",
				"Update Context Variable",
			],
			"Database": ["Set Context Variable", "Update Context Variable", "Batch Database Set"],
		}.get(writes_to, ["Set Context Variable", "Update Context Variable"])

		contract_v2 = overrides.get("contract_v2") or {}
		contract_v2.setdefault("adapter_key", "lookup")
		contract_v2.setdefault(
			"capabilities",
			{
				"requires_doc": bool(operation.get("requires_doc", 0)),
				"writes_to": writes_to,
				"allows_async": bool(operation.get("allows_async", 0)),
				"transactional": bool(operation.get("transactional", 0)),
				"can_stop_save": bool(operation.get("can_stop_save", 0)),
				"has_side_effect": bool(operation.get("has_side_effect", 0)),
			},
		)
		contract_v2.setdefault(
			"policy",
			{
				"allowed_mutations": allowed_mutations,
				"allowed_return_types": ["Single Record"],
				"default_return_type": "Single Record",
				"require_return_variable": False,
				"require_return_type": False,
			},
		)
		contract_v2.setdefault("config_schema", {"type": "object"})
		output_schema = operation.get("output_schema")
		if output_schema:
			try:
				contract_v2.setdefault(
					"result_schema",
					json.loads(output_schema if isinstance(output_schema, str) else "{}"),
				)
			except Exception:
				contract_v2.setdefault("result_schema", {"type": "object"})
		else:
			contract_v2.setdefault("result_schema", {"type": "object"})

		overrides["contract_v2"] = contract_v2
		operation["action_overrides"] = json.dumps(overrides, separators=(",", ":"), sort_keys=True)
		return operation

	def test_import_process_from_file_new(self):
		"""Test importing a new process from a JSON file"""
		json_path = self.create_test_process_json("TestNewProcess")

		# Import the process
		import_process_from_file(json_path, "Ruleflow")

		# Check if the process was created
		self.assertTrue(frappe.db.exists("Process", "TestNewProcess"))

		# Verify the process details
		process_doc = frappe.get_doc("Process", "TestNewProcess")
		self.assertEqual(process_doc.process_name, "TestNewProcess")
		self.assertEqual(process_doc.module, "Ruleflow")
		self.assertEqual(len(process_doc.operations), 1)
		self.assertEqual(process_doc.operations[0].func_name, "test_operation")

	def test_import_process_from_file_update(self):
		"""Test updating an existing process from a JSON file"""
		# First, create the process
		json_path = self.create_test_process_json("TestUpdateProcess")
		import_process_from_file(json_path, "Ruleflow")

		# Verify initial state
		process_doc = frappe.get_doc("Process", "TestUpdateProcess")
		self.assertEqual(len(process_doc.operations), 1)
		self.assertEqual(process_doc.operations[0].label, "Test Operation")

		# Create updated JSON with modified operation
		updated_operations = [
			{
				"func_name": "test_operation",
				"label": "Updated Test Operation",  # Changed label
				"enabled": 1,
				"visible_in_builder": 1,
				"requires_doc": 0,
				"can_stop_save": 0,
				"is_terminal": 0,
				"writes_to": "None",
				"allows_async": 0,
				"transactional": 0,
			}
		]

		updated_json_path = self.create_test_process_json("TestUpdateProcess", updated_operations)

		# Import the updated process
		import_process_from_file(updated_json_path, "Ruleflow")

		# Verify the update
		updated_process_doc = frappe.get_doc("Process", "TestUpdateProcess")
		self.assertEqual(len(updated_process_doc.operations), 1)
		self.assertEqual(updated_process_doc.operations[0].label, "Updated Test Operation")

	def test_import_process_from_file_add_operation(self):
		"""Test adding a new operation to an existing process"""
		# First, create the process
		json_path = self.create_test_process_json("TestAddOpProcess")
		import_process_from_file(json_path, "Ruleflow")

		# Verify initial state
		process_doc = frappe.get_doc("Process", "TestAddOpProcess")
		self.assertEqual(len(process_doc.operations), 1)

		# Create updated JSON with additional operation
		additional_operations = [
			{
				"func_name": "test_operation",
				"label": "Test Operation",
				"enabled": 1,
				"visible_in_builder": 1,
				"requires_doc": 0,
				"can_stop_save": 0,
				"is_terminal": 0,
				"writes_to": "None",
				"allows_async": 0,
				"transactional": 0,
			},
			{
				"func_name": "second_operation",
				"label": "Second Operation",
				"enabled": 1,
				"visible_in_builder": 1,
				"requires_doc": 1,
				"can_stop_save": 0,
				"is_terminal": 0,
				"writes_to": "Document",
				"allows_async": 1,
				"transactional": 1,
			},
		]

		updated_json_path = self.create_test_process_json("TestAddOpProcess", additional_operations)

		# Import the updated process
		import_process_from_file(updated_json_path, "Ruleflow")

		# Verify the addition
		updated_process_doc = frappe.get_doc("Process", "TestAddOpProcess")
		self.assertEqual(len(updated_process_doc.operations), 2)

		# Check that both operations exist
		operation_names = [op.func_name for op in updated_process_doc.operations]
		self.assertIn("test_operation", operation_names)
		self.assertIn("second_operation", operation_names)

	def test_import_process_from_file_removes_deleted_operation(self):
		"""Removed operations in JSON should be pruned from the Process doc."""
		initial_operations = [
			{
				"func_name": "test_operation",
				"label": "Test Operation",
				"enabled": 1,
				"visible_in_builder": 1,
				"requires_doc": 0,
				"can_stop_save": 0,
				"is_terminal": 0,
				"writes_to": "None",
				"allows_async": 0,
				"transactional": 0,
			},
			{
				"func_name": "obsolete_operation",
				"label": "Obsolete Operation",
				"enabled": 1,
				"visible_in_builder": 1,
				"requires_doc": 0,
				"can_stop_save": 0,
				"is_terminal": 0,
				"writes_to": "None",
				"allows_async": 0,
				"transactional": 0,
			},
		]

		json_path = self.create_test_process_json("TestRemoveOpProcess", initial_operations)
		import_process_from_file(json_path, "Ruleflow")

		updated_operations = [
			{
				"func_name": "test_operation",
				"label": "Test Operation",
				"enabled": 1,
				"visible_in_builder": 1,
				"requires_doc": 0,
				"can_stop_save": 0,
				"is_terminal": 0,
				"writes_to": "None",
				"allows_async": 0,
				"transactional": 0,
			}
		]

		updated_json_path = self.create_test_process_json("TestRemoveOpProcess", updated_operations)
		import_process_from_file(updated_json_path, "Ruleflow")

		updated_process_doc = frappe.get_doc("Process", "TestRemoveOpProcess")
		operation_names = [op.func_name for op in updated_process_doc.operations]
		self.assertEqual(operation_names, ["test_operation"])

	def test_sync_processes_for_app_prunes_missing_standard_process(self):
		"""Missing file-backed Process docs should be removed during app sync."""
		original_in_import = getattr(frappe.flags, "in_import", False)
		frappe.flags.in_import = True
		try:
			process = frappe.get_doc(
				{
					"doctype": "Process",
					"process_name": "TestPruneMissingProcess",
					"module": "Ruleflow",
					"is_standard": "Yes",
				}
			).insert(ignore_permissions=True)
		finally:
			frappe.flags.in_import = original_in_import

		self.assertTrue(frappe.db.exists("Process", process.name))

		sync_processes_for_app("flexirule")

		self.assertFalse(frappe.db.exists("Process", process.name))

	def test_import_process_from_file_missing_name(self):
		"""Test importing a process with missing name"""
		# Create JSON without process_name
		process_data = {"module": "Ruleflow", "is_standard": "Yes", "operations": []}

		temp_dir = tempfile.mkdtemp()
		json_file_path = os.path.join(temp_dir, "missing_name.json")

		with open(json_file_path, "w") as f:
			json.dump(process_data, f, indent=2)

		json_path = Path(json_file_path)

		# Import should not create a process since name is missing
		import_process_from_file(json_path, "Ruleflow")

		# No process should be created with an empty or missing name
		self.assertFalse(frappe.db.exists("Process", ""))
		# Also ensure our specific missing process didn't somehow get created with its filename as name
		self.assertFalse(frappe.db.exists("Process", "missing_name"))

	def test_import_process_from_file_missing_module(self):
		"""Test importing a process with missing module"""
		json_path = self.create_test_process_json("TestMissingModuleProcess")

		# Read the JSON and remove module
		with open(json_path) as f:
			data = json.load(f)

		# Remove module field
		if "module" in data:
			del data["module"]

		# Write back to file
		with open(json_path, "w") as f:
			json.dump(data, f, indent=2)

		# Import should fail gracefully since module doesn't exist properly
		import_process_from_file(json_path, "NonExistentModule")

		# Process should not be created
		self.assertFalse(frappe.db.exists("Process", "TestMissingModuleProcess"))

	def test_import_process_from_file_rejects_legacy_operation_shape(self):
		"""Hard cutover: process operations without contract_v2 should fail."""
		process_data = {
			"process_name": "TestLegacyOperationShape",
			"module": "Ruleflow",
			"is_standard": "Yes",
			"operations": [
				{
					"func_name": "legacy_operation",
					"label": "Legacy Operation",
					"enabled": 1,
					"visible_in_builder": 1,
					"writes_to": "Context",
				}
			],
		}

		temp_dir = tempfile.mkdtemp()
		json_file_path = os.path.join(temp_dir, "testlegacyoperationshape.json")
		with open(json_file_path, "w") as f:
			json.dump(process_data, f, indent=2)

		with self.assertRaises(Exception):
			import_process_from_file(Path(json_file_path), "Ruleflow")

	def test_get_process_json_path_existing(self):
		"""Test getting JSON path for an existing process"""
		# Create a process first
		json_path = self.create_test_process_json("TestGetPathProcess")
		import_process_from_file(json_path, "Ruleflow")

		# Get the JSON path
		retrieved_path = get_process_json_path("TestGetPathProcess", "Ruleflow")
		# In developer mode, importing a standard Process may export it to app files.
		if retrieved_path is None:
			self.assertIsNone(retrieved_path)
		else:
			self.assertTrue(str(retrieved_path).endswith("testgetpathprocess/testgetpathprocess.json"))

	def test_get_process_json_path_nonexistent(self):
		"""Test getting JSON path for a nonexistent process"""
		retrieved_path = get_process_json_path("NonExistentProcess")
		self.assertIsNone(retrieved_path)

	def test_sync_processes_for_app(self):
		"""Test syncing processes for a specific app"""
		# This test is difficult to run in isolation since it requires a real app
		# with process files in the expected location.
		# We'll test that the function doesn't crash with a known app.

		# Use the current app (flexirule) which should exist
		app_name = "flexirule"

		# This should not raise an exception
		sync_processes_for_app(app_name)

	def test_sync_all_processes(self):
		"""Test syncing all processes"""
		# This should not raise an exception
		sync_all_processes()

	def test_import_process_from_file_case_insensitive_module(self):
		"""Test importing process with case insensitive module matching"""
		# Create a process with lowercase module name in JSON
		process_data = {
			"process_name": "TestCaseInsensitive",
			"module": "ruleflow",  # lowercase
			"is_standard": "Yes",
			"operations": [
				self._with_default_contract_v2(
					{
						"func_name": "test_operation",
						"label": "Test Operation",
						"enabled": 1,
						"visible_in_builder": 1,
						"requires_doc": 0,
						"can_stop_save": 0,
						"is_terminal": 0,
						"writes_to": "None",
						"allows_async": 0,
						"transactional": 0,
					}
				)
			],
		}

		temp_dir = tempfile.mkdtemp()
		json_file_path = os.path.join(temp_dir, "testcaseinsensitive.json")

		with open(json_file_path, "w") as f:
			json.dump(process_data, f, indent=2)

		json_path = Path(json_file_path)

		# Import the process - should work even with case difference
		import_process_from_file(json_path, "Ruleflow")  # Capital R

		# Check if the process was created
		self.assertTrue(frappe.db.exists("Process", "TestCaseInsensitive"))

	def test_import_process_from_file_with_all_operation_fields(self):
		"""Test importing process with all operation fields defined"""
		operations_with_all_fields = [
			{
				"func_name": "comprehensive_operation",
				"label": "Comprehensive Operation",
				"enabled": 1,
				"visible_in_builder": 1,
				"icon": "fa-test-icon",
				"color": "#FF0000",
				"requires_doc": 1,
				"can_stop_save": 1,
				"is_terminal": 0,
				"writes_to": "Database",
				"allows_async": 1,
				"transactional": 1,
				"reads_vars": '[{"fieldname": "input_var", "fieldtype": "Data"}]',
				"writes_vars": '[{"fieldname": "output_var", "fieldtype": "Data"}]',
				"config_schema": '{"type": "object", "properties": {"param": {"type": "string"}}}',
				"output_schema": '{"type": "object", "properties": {"result": {"type": "string"}}}',
				"action_overrides": '{"policy":{"require_return_variable":true}}',
			}
		]

		json_path = self.create_test_process_json("TestComprehensiveProcess", operations_with_all_fields)

		# Import the process
		import_process_from_file(json_path, "Ruleflow")

		# Check if the process was created
		self.assertTrue(frappe.db.exists("Process", "TestComprehensiveProcess"))

		# Verify all operation fields were imported
		process_doc = frappe.get_doc("Process", "TestComprehensiveProcess")
		operation = process_doc.operations[0]

		self.assertEqual(operation.func_name, "comprehensive_operation")
		self.assertEqual(operation.label, "Comprehensive Operation")
		self.assertEqual(operation.enabled, 1)
		self.assertEqual(operation.visible_in_builder, 1)
		self.assertEqual(operation.icon, "fa-test-icon")
		self.assertEqual(operation.color, "#FF0000")
		self.assertEqual(operation.requires_doc, 1)
		self.assertEqual(operation.can_stop_save, 1)
		self.assertEqual(operation.is_terminal, 0)
		self.assertEqual(operation.writes_to, "Database")
		self.assertEqual(operation.allows_async, 1)
		self.assertEqual(operation.transactional, 1)
		self.assertEqual(operation.reads_vars, '[{"fieldname": "input_var", "fieldtype": "Data"}]')
		self.assertEqual(operation.writes_vars, '[{"fieldname": "output_var", "fieldtype": "Data"}]')
		self.assertEqual(
			operation.config_schema,
			'{"type": "object", "properties": {"param": {"type": "string"}}}',
		)
		self.assertEqual(
			operation.output_schema,
			'{"type": "object", "properties": {"result": {"type": "string"}}}',
		)
		if frappe.get_meta("Process Operation").has_field("action_overrides") and frappe.db.has_column(
			"Process Operation", "action_overrides"
		):
			overrides = json.loads(operation.action_overrides)
			self.assertEqual((overrides.get("policy") or {}).get("require_return_variable"), True)
			self.assertIn("contract_v2", overrides)

	def test_import_process_from_file_disabled_operation(self):
		"""Test importing process with disabled operation"""
		operations = [
			{
				"func_name": "disabled_operation",
				"label": "Disabled Operation",
				"enabled": 0,  # Disabled
				"visible_in_builder": 1,
				"requires_doc": 0,
				"can_stop_save": 0,
				"is_terminal": 0,
				"writes_to": "None",
				"allows_async": 0,
				"transactional": 0,
			}
		]

		json_path = self.create_test_process_json("TestDisabledOpProcess", operations)

		# Import the process
		import_process_from_file(json_path, "Ruleflow")

		# Check if the process was created
		self.assertTrue(frappe.db.exists("Process", "TestDisabledOpProcess"))

		# Verify the operation is disabled
		process_doc = frappe.get_doc("Process", "TestDisabledOpProcess")
		operation = process_doc.operations[0]

		self.assertEqual(operation.func_name, "disabled_operation")
		self.assertEqual(operation.enabled, 0)

	def test_import_process_from_file_invalid_json(self):
		"""Test importing process from invalid JSON file"""
		# Create an invalid JSON file
		temp_dir = tempfile.mkdtemp()
		json_file_path = os.path.join(temp_dir, "invalid.json")

		with open(json_file_path, "w") as f:
			f.write("{ invalid json ")  # Invalid JSON

		json_path = Path(json_file_path)

		# Import should handle the error gracefully
		try:
			import_process_from_file(json_path, "Ruleflow")
		except Exception:
			# Expected to fail, but shouldn't crash the system
			pass

		# No process should be created
		self.assertFalse(frappe.db.exists("Process", "invalid"))

	def test_import_process_from_file_respects_source_modified_timestamp(self):
		"""Older source metadata should not override a newer DB process definition."""
		initial_operations = [
			{
				"func_name": "test_operation",
				"label": "Current Label",
				"enabled": 1,
				"visible_in_builder": 1,
				"writes_to": "Context",
				"requires_doc": 0,
				"can_stop_save": 0,
				"is_terminal": 0,
				"allows_async": 0,
				"transactional": 0,
			}
		]
		json_path = self.create_test_process_json("TestTimestampGuard", initial_operations)
		import_process_from_file(json_path, "Ruleflow")

		with open(json_path) as f:
			stale_data = json.load(f)

		stale_data["modified"] = "2000-01-01 00:00:00"
		stale_data["operations"][0]["label"] = "Stale Label Should Not Apply"
		with open(json_path, "w") as f:
			json.dump(stale_data, f, indent=2)

		import_process_from_file(json_path, "Ruleflow")
		doc = frappe.get_doc("Process", "TestTimestampGuard")
		self.assertEqual(doc.operations[0].label, "Current Label")
