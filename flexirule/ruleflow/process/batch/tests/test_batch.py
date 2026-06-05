# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

import json

import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.process.batch.batch import (
	execute_for_documents,
)


class TestBatchProcess(FrappeTestCase):
	def setUp(self):
		if not frappe.db.exists("Rule", "Test Batch Rule"):
			self.rule = frappe.get_doc(
				{
					"doctype": "Rule",
					"rule_name": "Test Batch Rule",
					"document_type": "ToDo",
					"trigger_type": "DocType Event",
					"trigger_event": "Before Save",
					"is_active": 1,
					"actions": [
						{
							"action_type": "Entry Action",
							"config": '[{"target": "doc.priority", "operator": "set", "value": "High"}]',
							"action_label": "Make High Priority",
							"action_id": "root",
							"next_step_if_true": None,
						}
					],
				}
			).insert(ignore_permissions=True)
		else:
			self.rule = frappe.get_doc("Rule", "Test Batch Rule")

		# Create test docs
		self.todo1 = frappe.get_doc({"doctype": "ToDo", "description": "Batch Proc 1"}).insert()
		self.todo2 = frappe.get_doc({"doctype": "ToDo", "description": "Batch Proc 2"}).insert()

	def tearDown(self):
		frappe.db.rollback()

	def test_execute_for_documents(self):
		config = {
			"rule": self.rule.name,
			"doctype": "ToDo",
			"documents": [self.todo1.name, self.todo2.name],
			"batch_size": 10,
		}

		result = execute_for_documents({}, config)
		self.assertEqual(result["success"], 2)
		self.assertEqual(result["failed"], 0)
		self.assertTrue(result["batch_id"].startswith("BATCH-PROC-"))

		# Verify logs
		logs = frappe.get_all(
			"Rule Execution Log",
			filters={"batch_id": result["batch_id"]},
			fields=["reference_docname"],
		)
		self.assertEqual(len(logs), 2)

	def test_json_parsing(self):
		# Test string input for documents/filters (common from UI/API)
		config = {
			"rule": self.rule.name,
			"doctype": "ToDo",
			"documents": json.dumps([self.todo1.name]),
		}
		result = execute_for_documents({}, config)
		self.assertEqual(result["success"], 1)
