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
	Serialization, and Database Execution.
	"""

	_created_doctypes: ClassVar[list[str]] = []

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls._setup_test_doctypes()
		cls._setup_test_records()

	@classmethod
	def tearDownClass(cls):
		frappe.db.delete("QB Tree Parent")

		for dt in cls._created_doctypes:
			if frappe.db.exists("DocType", dt):
				frappe.delete_doc(dt, force=True, ignore_permissions=True)

		frappe.db.commit()
		super().tearDownClass()

	@classmethod
	def _setup_test_doctypes(cls):
		dt = "QB Tree Parent"
		if not frappe.db.exists("DocType", dt):
			frappe.get_doc(
				{
					"doctype": "DocType",
					"name": dt,
					"module": "RuleFlow",
					"custom": 1,
					"fields": [
						{"fieldname": "title", "fieldtype": "Data", "label": "Title"},
						{
							"fieldname": "status",
							"fieldtype": "Select",
							"options": "Open\nPending\nClosed",
							"label": "Status",
						},
						{
							"fieldname": "priority",
							"fieldtype": "Select",
							"options": "High\nLow",
							"label": "Priority",
						},
						{"fieldname": "score", "fieldtype": "Int", "label": "Score"},
					],
				}
			).insert(ignore_permissions=True)
			cls._created_doctypes.append(dt)

		frappe.db.commit()

	@classmethod
	def _setup_test_records(cls):
		frappe.db.delete("QB Tree Parent")

		cls.t1 = frappe.get_doc(
			{
				"doctype": "QB Tree Parent",
				"title": "Task 1",
				"status": "Open",
				"priority": "High",
				"score": 100,
			}
		).insert(ignore_permissions=True)

		cls.t2 = frappe.get_doc(
			{
				"doctype": "QB Tree Parent",
				"title": "Task 2",
				"status": "Pending",
				"priority": "Low",
				"score": 50,
			}
		).insert(ignore_permissions=True)

		cls.t3 = frappe.get_doc(
			{
				"doctype": "QB Tree Parent",
				"title": "Task 3",
				"status": "Closed",
				"priority": "Low",
				"score": 10,
			}
		).insert(ignore_permissions=True)

		frappe.db.commit()

	def test_01_canonical_json_tree_execution(self):
		"""Execute JSON filter tree through Fetch Records handler."""
		tree_data = {
			"type": "group",
			"operator": "and",
			"children": [
				{
					"type": "leaf",
					"doctype": "QB Tree Parent",
					"field": "title",
					"operator": "starts with",
					"value": {"value": "Task"},
				},
				{
					"type": "group",
					"operator": "or",
					"children": [
						{
							"type": "leaf",
							"doctype": "QB Tree Parent",
							"field": "status",
							"operator": "=",
							"value": {"value": "Open"},
						},
						{
							"type": "leaf",
							"doctype": "QB Tree Parent",
							"field": "score",
							"operator": ">=",
							"value": {"value": 50},
						},
					],
				},
			],
		}

		handler = QueryRecordsHandler()

		class DummyAction:
			label = "Test Action"

		res = handler._fetch_records(
			reference_doctype="QB Tree Parent",
			config={"fields": ["name", "title"], "filters": tree_data},
			context={},
			action=DummyAction(),
			ignore_permissions=True,
		)

		self.assertEqual(len(res), 2)
		names = {r["name"] for r in res}
		self.assertIn(self.t1.name, names)
		self.assertIn(self.t2.name, names)

	def test_02_three_level_deep_logical_tree_execution(self):
		"""3-level deep nested tree: title starts with 'Task' AND (priority='High' OR (status='Pending' AND score=50))."""
		tree_data = {
			"type": "group",
			"operator": "and",
			"children": [
				{
					"type": "leaf",
					"doctype": "QB Tree Parent",
					"field": "title",
					"operator": "like",
					"value": "Task%",
				},
				{
					"type": "group",
					"operator": "or",
					"children": [
						{
							"type": "leaf",
							"doctype": "QB Tree Parent",
							"field": "priority",
							"operator": "=",
							"value": "High",
						},
						{
							"type": "group",
							"operator": "and",
							"children": [
								{
									"type": "leaf",
									"doctype": "QB Tree Parent",
									"field": "status",
									"operator": "=",
									"value": "Pending",
								},
								{
									"type": "leaf",
									"doctype": "QB Tree Parent",
									"field": "score",
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
		backend_filters = handler._canonical_filter_tree_to_backend(tree_data, "QB Tree Parent")

		res = execute_query(
			doctype="QB Tree Parent",
			kwargs={"fields": ["name"], "filters": backend_filters},
			ignore_permissions=True,
		)

		self.assertEqual(len(res), 2)
		names = {r["name"] for r in res}
		self.assertIn(self.t1.name, names)
		self.assertIn(self.t2.name, names)
