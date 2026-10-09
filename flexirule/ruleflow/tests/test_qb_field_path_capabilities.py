# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

import uuid
from typing import ClassVar

import frappe
from frappe.tests.utils import FrappeTestCase


class TestQBFieldPathCapabilities(FrappeTestCase):
	"""
	Empirical Test Suite: Field Path Capabilities and Relationship Depth Limits
	in frappe.qb.get_query() using installed DocTypes (Rule, Rule Action, Process).
	"""

	_created_records: ClassVar[list[tuple[str, str]]] = []
	_run_id: ClassVar[str] = ""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls._created_records = []
		cls._run_id = uuid.uuid4().hex[:8].upper()
		cls._setup_test_records()

	@classmethod
	def tearDownClass(cls):
		for doctype, docname in reversed(cls._created_records):
			if frappe.db.exists(doctype, docname):
				frappe.delete_doc(doctype, docname, force=True, ignore_permissions=True)

		cls._created_records.clear()
		frappe.db.commit()
		super().tearDownClass()

	@classmethod
	def _setup_test_records(cls):
		proc_name = f"_TEST_QB_PROC_{cls._run_id}"
		rule_name = f"_TEST_QB_PATH_{cls._run_id}_PARENT"

		if frappe.db.exists("Process", proc_name):
			raise RuntimeError(f"Unexpected pre-existing Process record: {proc_name}")
		if frappe.db.exists("Rule", rule_name):
			raise RuntimeError(f"Unexpected pre-existing Rule record: {rule_name}")

		proc = frappe.get_doc(
			{
				"doctype": "Process",
				"process_name": proc_name,
				"module": "Ruleflow",
				"description": "North Region Process",
			}
		).insert(ignore_permissions=True)
		cls._created_records.append(("Process", proc.name))

		rule = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": rule_name,
				"priority": "10",
				"trigger_type": "DocType Event",
				"document_type": "User",
				"trigger_event": "Validate",
				"execution_mode": "Synchronous",
				"actions": [
					{
						"action_id": "act_test_1",
						"action_label": "Test Action 1",
						"action_type": "Process",
						"process_name": proc.name,
					}
				],
			}
		).insert(ignore_permissions=True)
		cls._created_records.append(("Rule", rule.name))

		cls.proc_name = proc.name
		cls.rule_name = rule.name

		frappe.db.commit()

	def test_01_one_level_link_path_selection_and_filtering(self):
		"""1-level Link path ('process_name.description') is supported in both select and filters on Rule Action."""
		q = frappe.qb.get_query(
			"Rule Action",
			fields=["name", "action_id", "process_name.description"],
			filters={"parent": self.rule_name, "process_name.description": "North Region Process"},
		)
		sql = q.get_sql()
		self.assertIn("LEFT JOIN `tabProcess`", sql)

		res = q.run(as_dict=True)
		self.assertEqual(len(res), 1)
		self.assertEqual(res[0]["action_id"], "act_test_1")
		self.assertEqual(res[0]["description"], "North Region Process")

	def test_02_multi_level_link_path_failure_stage(self):
		"""Multi-level link path ('process_name.module.app_name') fails during DynamicTableField.parse stage."""
		# DynamicTableField.parse does linked_fieldname, fieldname = field.split(".")
		# With >1 dot, field.split(".") produces 3+ parts, raising ValueError ("too many values to unpack").
		with self.assertRaises(ValueError) as ctx:
			frappe.qb.get_query(
				"Rule Action",
				fields=["name", "process_name.module.app_name"],
			)
		self.assertIn("too many values to unpack", str(ctx.exception))

	def test_03_child_table_field_selection_and_filtering(self):
		"""Direct child table field path ('actions.action_id') is supported natively when querying parent Rule."""
		q = frappe.qb.get_query(
			"Rule",
			fields=["name", "actions.action_id"],
			filters={"rule_name": self.rule_name, "actions.action_id": "act_test_1"},
		)
		sql = q.get_sql()
		self.assertIn("LEFT JOIN `tabRule Action`", sql)

		res = q.run(as_dict=True)
		self.assertEqual(len(res), 1)
		self.assertEqual(res[0]["name"], self.rule_name)
		self.assertEqual(res[0]["action_id"], "act_test_1")

	def test_04_child_table_link_field_path_failure_stage(self):
		"""Link field inside child table path ('actions.process_name.description') fails during parse."""
		with self.assertRaises(ValueError) as ctx:
			frappe.qb.get_query(
				"Rule",
				fields=["name", "actions.process_name.description"],
			)
		self.assertIn("too many values to unpack", str(ctx.exception))

	def test_05_direct_child_query_parent_field(self):
		"""Querying child table directly allows selecting 'parent' column as data string."""
		q = frappe.qb.get_query(
			"Rule Action",
			fields=["name", "action_id", "parent"],
			filters={"parent": self.rule_name, "action_id": "act_test_1"},
		)
		res = q.run(as_dict=True)
		self.assertEqual(len(res), 1)
		self.assertEqual(res[0]["parent"], self.rule_name)
