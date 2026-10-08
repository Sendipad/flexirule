# Copyright (c) 2026, FlexiRule and contributors

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.core.action_handlers.query_records import QueryRecordsHandler


class TestCanonicalQueryRecordFilters(FrappeTestCase):
	def setUp(self):
		self.handler = QueryRecordsHandler()
		self.context = {"doc": frappe._dict(), "vars": {}}
		self.action = frappe._dict({"name": "ACT001", "label": "TestQuery", "config": "{}"})

	def _config(self):
		return {
			"filters": {
				"type": "group",
				"operator": "or",
				"children": [
					{
						"type": "leaf",
						"doctype": "User",
						"field": "first_name",
						"operator": "starts with",
						"value": {"mode": "static", "value": "Admin"},
					},
					{
						"type": "leaf",
						"doctype": "User",
						"field": "enabled",
						"operator": "=",
						"value": {"mode": "static", "value": 1},
					},
				],
			}
		}

	def test_canonical_filter_tree_normalizes_for_query_modes(self):
		expected = [
			["User", "first_name", "like", "Admin%"],
			"or",
			["User", "enabled", "=", 1],
		]
		config = self._config()

		with patch("frappe.get_list", return_value=[]) as mock_get_list:
			self.handler._query_list("User", config, self.context, self.action, ignore_permissions=True)
			self.assertEqual(mock_get_list.call_args.kwargs["filters"], expected)

		with patch("frappe.get_all", return_value=[]) as mock_get_all:
			self.handler._query_doc(
				"User",
				dict(config, fetch_strategy="Get latest Doc"),
				self.context,
				self.action,
				ignore_permissions=True,
			)
			self.assertEqual(mock_get_all.call_args.kwargs["filters"], expected)

		for operation, method_name in (
			("Exist Record", "_exist_record"),
			("Count", "_count_records"),
			("Sum", "_aggregate"),
			("Group By", "_group_by"),
		):
			self.action.operation = operation
			mode_config = dict(config)
			if operation == "Sum":
				mode_config["field"] = "enabled"
			elif operation == "Group By":
				mode_config.update({"field": "name", "group_by_field": "enabled"})

			with patch("frappe.get_list", return_value=[]) as mock_get_list:
				getattr(self.handler, method_name)(
					"User", mode_config, self.context, self.action, ignore_permissions=True
				)
				self.assertEqual(mock_get_list.call_args.kwargs["filters"], expected)
