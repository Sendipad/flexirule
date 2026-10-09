# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

import uuid
from typing import ClassVar

import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.core.action_handlers.query_records import QueryRecordsHandler


class TestFetchRecordsFilterTreeIntegration(FrappeTestCase):
	"""
	Empirical Test Suite: End-to-End Filter Tree Integration,
	Serialization, and Database Execution using installed Rule DocType.
	"""

	_created_records: ClassVar[list[tuple[str, str]]] = []
	_run_id: ClassVar[str] = ""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls._created_records = []
		cls.addClassCleanup(cls._cleanup_resources)
		cls._run_id = uuid.uuid4().hex[:8].upper()
		cls._setup_test_records()

	@classmethod
	def _cleanup_resources(cls):
		for doctype, docname in reversed(cls._created_records):
			if frappe.db.exists(doctype, docname):
				frappe.delete_doc(doctype, docname, force=True, ignore_permissions=True)

		cls._created_records.clear()
		frappe.db.commit()

	@classmethod
	def _setup_test_records(cls):
		prefix = f"_TEST_QB_TREE_{cls._run_id}_"

		records = [
			{
				"rule_name": f"{prefix}RULE_1",
				"execution_mode": "Synchronous",
				"priority": "10",
				"max_execution_time": 100,
				"description": "Task 1",
			},
			{
				"rule_name": f"{prefix}RULE_2",
				"execution_mode": "Asynchronous",
				"priority": "1",
				"max_execution_time": 50,
				"description": "Task 2",
			},
			{
				"rule_name": f"{prefix}RULE_3",
				"execution_mode": "Synchronous",
				"priority": "1",
				"max_execution_time": 10,
				"description": "Task 3",
			},
		]

		for data in records:
			rule_name = data["rule_name"]
			if frappe.db.exists("Rule", rule_name):
				raise RuntimeError(f"Unexpected pre-existing Rule record: {rule_name}")

			doc = frappe.get_doc(
				{
					"doctype": "Rule",
					"rule_name": rule_name,
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

		cls.prefix = prefix
		cls.rule1 = records[0]["rule_name"]
		cls.rule2 = records[1]["rule_name"]
		cls.rule3 = records[2]["rule_name"]

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
					"value": {"mode": "static", "value": self.prefix},
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
							"value": {"mode": "static", "value": "Asynchronous"},
						},
						{
							"type": "leaf",
							"doctype": "Rule",
							"field": "max_execution_time",
							"operator": ">=",
							"value": {"mode": "static", "value": 100},
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
		self.assertIn(self.rule1, names)
		self.assertIn(self.rule2, names)

	def test_02_three_level_deep_logical_tree_execution(self):
		"""3-level deep nested tree through Fetch Records handler: prefix match AND (priority='10' OR (execution_mode='Asynchronous' AND max_execution_time=50))."""
		tree_data = {
			"type": "group",
			"operator": "and",
			"children": [
				{
					"type": "leaf",
					"doctype": "Rule",
					"field": "rule_name",
					"operator": "like",
					"value": f"{self.prefix}%",
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
		self.assertIn(self.rule1, names)
		self.assertIn(self.rule2, names)

	def test_03_legacy_tuple_and_list_filter_shapes_are_rejected(self):
		"""Fetch Records must reject legacy filter formats rather than normalize them."""
		handler = QueryRecordsHandler()

		class DummyAction:
			label = "Test Action"

		legacy_filters = [
			["rule_name", "in", [self.rule1, self.rule3]],
			["execution_mode", "=", "Synchronous"],
		]

		with self.assertRaises(frappe.ValidationError):
			handler._fetch_records(
				reference_doctype="Rule",
				config={"fields": ["name", "rule_name"], "filters": legacy_filters},
				context={},
				action=DummyAction(),
				ignore_permissions=True,
			)

	def test_04_json_object_filter_values_are_valid(self):
		"""Raw JSON object values are not mistaken for malformed FlexValue wrappers."""
		handler = QueryRecordsHandler()
		leaf = {
			"type": "leaf",
			"field": "description",
			"operator": "=",
			"value": {"custom": "payload", "enabled": True},
		}
		self.assertEqual(handler._validate_canonical_fetch_filter_tree(leaf), [])

	def test_05_static_flexvalue_requires_value_key(self):
		"""A FlexValue wrapper must include its value key even when the value is null."""
		handler = QueryRecordsHandler()
		leaf = {
			"type": "leaf",
			"field": "description",
			"operator": "=",
			"value": {"mode": "static"},
		}
		errors = handler._validate_canonical_fetch_filter_tree(leaf)
		self.assertTrue(any("value.value is required" in error for error in errors))
