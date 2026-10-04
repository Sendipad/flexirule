# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import random_string

from flexirule.ruleflow.core.action_handlers.query_records import QueryRecordsHandler
from flexirule.ruleflow.tests.test_frappe_qb_capabilities import TestFrappeQBCapabilities


class TestFetchRecords(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		TestFrappeQBCapabilities.setUpClass()

	@classmethod
	def tearDownClass(cls):
		TestFrappeQBCapabilities.tearDownClass()
		super().tearDownClass()

	def setUp(self):
		self.handler = QueryRecordsHandler()

	def tearDown(self):
		frappe.db.rollback()

	def test_fetch_records_default_name_field(self):
		action = frappe._dict(
			{
				"operation": "Fetch Records",
				"reference_doctype": "QB Test Parent",
				"config": frappe.as_json({}),
			}
		)
		result, _ = self.handler.execute(action, {}, None)
		self.assertIsInstance(result, list)
		if result:
			self.assertIn("name", result[0])

	def test_fetch_records_select_all(self):
		action = frappe._dict(
			{
				"operation": "Fetch Records",
				"reference_doctype": "QB Test Parent",
				"config": frappe.as_json({"select_all": True}),
			}
		)
		result, _ = self.handler.execute(action, {}, None)
		self.assertIsInstance(result, list)
		if result:
			self.assertIn("name", result[0])
			self.assertIn("status", result[0])

	def test_fetch_records_individual_fields(self):
		action = frappe._dict(
			{
				"operation": "Fetch Records",
				"reference_doctype": "QB Test Parent",
				"config": frappe.as_json({"fields": ["name", "status"]}),
			}
		)
		result, _ = self.handler.execute(action, {}, None)
		self.assertIsInstance(result, list)
		if result:
			self.assertIn("name", result[0])
			self.assertIn("status", result[0])

	def test_fetch_records_nested_link_field(self):
		action = frappe._dict(
			{
				"operation": "Fetch Records",
				"reference_doctype": "QB Test Parent",
				"config": frappe.as_json({"fields": ["name", "target_link.territory"]}),
			}
		)
		result, _ = self.handler.execute(action, {}, None)
		self.assertIsInstance(result, list)
		if result:
			self.assertIn("name", result[0])
			self.assertIn("territory", result[0])

	def test_fetch_records_nested_child_table_field(self):
		action = frappe._dict(
			{
				"operation": "Fetch Records",
				"reference_doctype": "QB Test Parent",
				"config": frappe.as_json({"fields": ["name", "items.item_code"]}),
			}
		)
		result, _ = self.handler.execute(action, {}, None)
		self.assertIsInstance(result, list)
		if result:
			self.assertIn("name", result[0])
			self.assertIn("item_code", result[0])

	def test_fetch_records_function_and_alias(self):
		action = frappe._dict(
			{
				"operation": "Fetch Records",
				"reference_doctype": "QB Test Parent",
				"config": frappe.as_json(
					{
						"fields": [
							"name",
							{"field": "name", "function": "COUNT", "alias": "record_count"},
						]
					}
				),
			}
		)
		result, _ = self.handler.execute(action, {}, None)
		self.assertIsInstance(result, list)
		if result:
			self.assertIn("record_count", result[0])

	def test_fetch_records_empty_filters(self):
		action = frappe._dict(
			{
				"operation": "Fetch Records",
				"reference_doctype": "QB Test Parent",
				"config": frappe.as_json({"filters": {"logic": "ALL", "conditions": []}}),
			}
		)
		result, _ = self.handler.execute(action, {}, None)
		self.assertIsInstance(result, list)

	def test_fetch_records_nested_and_or_filter_tree(self):
		action = frappe._dict(
			{
				"operation": "Fetch Records",
				"reference_doctype": "QB Test Parent",
				"config": frappe.as_json(
					{
						"filters": {
							"logic": "ALL",
							"conditions": [
								{"field": "status", "operator": "=", "value": "Open"},
								{
									"logic": "ANY",
									"conditions": [
										{"field": "enabled", "operator": "=", "value": 1},
										{"field": "enabled", "operator": "=", "value": 0},
									],
								},
							],
						}
					}
				),
			}
		)
		result, _ = self.handler.execute(action, {}, None)
		self.assertIsInstance(result, list)

	def test_fetch_records_between_operator(self):
		action = frappe._dict(
			{
				"operation": "Fetch Records",
				"reference_doctype": "QB Test Parent",
				"config": frappe.as_json(
					{
						"filters": {
							"logic": "ALL",
							"conditions": [
								{"field": "creation", "operator": "Between", "value": ["2020-01-01", "2030-12-31"]}
							],
						}
					}
				),
			}
		)
		result, _ = self.handler.execute(action, {}, None)
		self.assertIsInstance(result, list)

	def test_fetch_records_order_by_and_limit(self):
		action = frappe._dict(
			{
				"operation": "Fetch Records",
				"reference_doctype": "QB Test Parent",
				"config": frappe.as_json({"fields": ["name"], "order_by": "creation desc", "limit": 2}),
			}
		)
		result, _ = self.handler.execute(action, {}, None)
		self.assertIsInstance(result, list)
		self.assertLessEqual(len(result), 2)

	def test_fetch_records_filter_on_nested_link_field(self):
		action = frappe._dict(
			{
				"operation": "Fetch Records",
				"reference_doctype": "QB Test Parent",
				"config": frappe.as_json(
					{
						"fields": ["name", "target_link.territory"],
						"filters": {
							"logic": "ALL",
							"conditions": [
								{"field": "target_link.territory", "operator": "=", "value": "North"}
							],
						},
					}
				),
			}
		)
		result, _ = self.handler.execute(action, {}, None)
		self.assertIsInstance(result, list)

	def test_fetch_records_filter_on_child_table_field(self):
		action = frappe._dict(
			{
				"operation": "Fetch Records",
				"reference_doctype": "QB Test Parent",
				"config": frappe.as_json(
					{
						"fields": ["name", "items.item_code"],
						"filters": {
							"logic": "ALL",
							"conditions": [
								{"field": "items.item_code", "operator": "=", "value": "ITEM-001"}
							],
						},
						"order_by": "items.item_code asc",
					}
				),
			}
		)
		result, _ = self.handler.execute(action, {}, None)
		self.assertIsInstance(result, list)
