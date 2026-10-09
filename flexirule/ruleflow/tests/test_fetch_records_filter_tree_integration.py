# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

from typing import ClassVar

import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.core.action_handlers.query_records import QueryRecordsHandler
from flexirule.ruleflow.utils.frappe_query_compat import execute_query


class TestFetchRecordsFilterTreeIntegration(FrappeTestCase):
	"""
	Empirical Test Suite: End-to-End Filter Tree Integration,
	Serialization, and Database Execution using installed Rule DocType.
	"""

	_created_records: ClassVar[list[tuple[str, str]]] = []

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls._created_records = []
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
		records = [
			{
				"rule_name": "_TEST_QB_TREE_RULE_1",
				"execution_mode": "Synchronous",
				"priority": "10",
				"max_execution_time": 100,
				"description": "Task 1",
			},
			{
				"rule_name": "_TEST_QB_TREE_RULE_2",
				"execution_mode": "Asynchronous",
				"priority": "1",
				"max_execution_time": 50,
				"description": "Task 2",
			},
			{
				"rule_name": "_TEST_QB_TREE_RULE_3",
				"execution_mode": "Synchronous",
				"priority": "1",
				"max_execution_time": 10,
				"description": "Task 3",
			},
		]

		for data in records:
			if frappe.db.exists("Rule", data["rule_name"]):
				frappe.delete_doc("Rule", data["rule_name"], force=True, ignore_permissions=True)

			doc = frappe.get_doc(
				{
					"doctype": "Rule",
					"rule_name": data["rule_name"],
					"execution_mode": data["execution_mode"],
					"priority": data["priority"],
					"max_execution_time": data["max_execution_time"],
					"description": data["description"],
					"trigger_type": "DocType Event",
					"document_type": "User",
					"trigger_event": "Validate",
				}
			).insert(ignore_permissions=True)

			cls._created_records.append(("Rule", doc.name))

		frappe.db.commit()

	def test_01_canonical_json_tree_execution(self):
		"""Execute JSON filter tree through Fetch Records handler on Rule DocType."""
		tree_data = {
			"type": "group",
			"operator": "and",
			"children": [
				{
					"type": "leaf",
					"doctype": "Rule",
					"field": "rule_name",
					"operator": "starts with",
					"value": {"value": "_TEST_QB_TREE_RULE_"},
				},
				{
					"type": "group",
					"operator": "or",
					"children": [
						{
							"type": "leaf",
							"doctype": "Rule",
							"field": "execution_mode",
							"operator": "=",
							"value": {"value": "Asynchronous"},
						},
						{
							"type": "leaf",
							"doctype": "Rule",
							"field": "max_execution_time",
							"operator": ">=",
							"value": {"value": 100},
						},
					],
				},
			],
		}

		handler = QueryRecordsHandler()

		class DummyAction:
			label = "Test Action"

		res = handler._fetch_records(
			reference_doctype="Rule",
			config={"fields": ["name", "rule_name"], "filters": tree_data},
			context={},
			action=DummyAction(),
			ignore_permissions=True,
		)

		self.assertEqual(len(res), 2)
		names = {r["name"] for r in res}
		self.assertIn("_TEST_QB_TREE_RULE_1", names)
		self.assertIn("_TEST_QB_TREE_RULE_2", names)

	def test_02_three_level_deep_logical_tree_execution(self):
		"""3-level deep nested tree: rule_name starts with '_TEST_QB_TREE_RULE_' AND (priority='10' OR (execution_mode='Asynchronous' AND max_execution_time=50))."""
		tree_data = {
			"type": "group",
			"operator": "and",
			"children": [
				{
					"type": "leaf",
					"doctype": "Rule",
					"field": "rule_name",
					"operator": "like",
					"value": "_TEST_QB_TREE_RULE_%",
				},
				{
					"type": "group",
					"operator": "or",
					"children": [
						{
							"type": "leaf",
							"doctype": "Rule",
							"field": "priority",
							"operator": "=",
							"value": "10",
						},
						{
							"type": "group",
							"operator": "and",
							"children": [
								{
									"type": "leaf",
									"doctype": "Rule",
									"field": "execution_mode",
									"operator": "=",
									"value": "Asynchronous",
								},
								{
									"type": "leaf",
									"doctype": "Rule",
									"field": "max_execution_time",
									"operator": "=",
									"value": 50,
								},
							],
						},
					],
				},
			],
		}

		handler = QueryRecordsHandler()
		backend_filters = handler._canonical_filter_tree_to_backend(tree_data, "Rule")

		res = execute_query(
			doctype="Rule",
			kwargs={"fields": ["name"], "filters": backend_filters},
			ignore_permissions=True,
		)

		self.assertEqual(len(res), 2)
		names = {r["name"] for r in res}
		self.assertIn("_TEST_QB_TREE_RULE_1", names)
		self.assertIn("_TEST_QB_TREE_RULE_2", names)
