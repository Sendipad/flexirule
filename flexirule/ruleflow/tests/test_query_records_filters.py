# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

import unittest
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.core.action_handlers.query_records import QueryRecordsHandler


class TestQueryRecordsFilters(FrappeTestCase):
	def setUp(self):
		self.handler = QueryRecordsHandler()
		self.context = {
			"doc": frappe._dict({"status": "Open", "limit_val": 10}),
			"vars": {"search_term": "Flexi", "min_amount": 50, "max_amount": 100},
		}
		self.action = frappe._dict({"name": "ACT001", "label": "TestQuery", "config": "{}"})
		# Clear resolver cache
		if hasattr(frappe.local, "flexirule_compiled_resolvers"):
			delattr(frappe.local, "flexirule_compiled_resolvers")

	def test_resolve_simple_dict_filters(self):
		# Let's test with resolvers which is the recommended way
		config = {
			"filters": {
				"status": {"mode": "variable", "path": "doc.status"},
				"amount": [
					"Between",
					[
						{"mode": "variable", "path": "vars.min_amount"},
						{"mode": "variable", "path": "vars.max_amount"},
					],
				],
			}
		}

		filters, _ = self.handler._resolve_query_filters(config, self.context, self.action)

		# Should be normalized to [[field, op, val], ...]
		self.assertIn(["status", "=", "Open"], filters)
		# amount should be normalized to ['amount', 'between', [50, 100]]
		self.assertIn(["amount", "between", [50, 100]], filters)

	def test_resolve_list_of_dict_filters(self):
		config = {
			"filters": [
				{"fieldname": "status", "operator": "=", "value": {"mode": "variable", "path": "doc.status"}},
				{"field": "name", "operator": "like", "value": "{vars.search_term}%"},
			]
		}
		filters, _ = self.handler._resolve_query_filters(config, self.context, self.action)

		self.assertIn(["status", "=", "Open"], filters)
		self.assertIn(["name", "like", "Flexi%"], filters)

	def test_operator_normalization(self):
		config = {
			"filters": [
				["name", "starts with", "ABC"],
				["name", "ends with", "XYZ"],
				["amount", "Between", [10, 20]],
			]
		}
		filters, _ = self.handler._resolve_query_filters(config, self.context, self.action)

		self.assertIn(["name", "like", "ABC%"], filters)
		self.assertIn(["name", "like", "%XYZ"], filters)
		self.assertIn(["amount", "between", [10, 20]], filters)

	def test_timespan_normalization(self):
		config = {"filters": [["creation", "Timespan", "today"]]}
		# Patch nowdate in the module where it is imported
		with patch(
			"flexirule.ruleflow.core.action_handlers.query_records.nowdate", return_value="2026-05-20"
		):
			filters, _ = self.handler._resolve_query_filters(config, self.context, self.action)
			self.assertEqual(filters[0][1], "between")
			# [getdate("2026-05-20"), getdate("2026-05-20")]
			self.assertEqual(str(filters[0][2][0]), "2026-05-20")

	def test_boolean_payload_extraction(self):
		config = {"filters": [["is_active", "=", {"value": "Yes", "value_type": "Boolean"}]]}
		filters, _ = self.handler._resolve_query_filters(config, self.context, self.action)
		self.assertEqual(filters[0][2], 1)

		config["filters"] = [["is_active", "=", {"value": "false", "value_type": "Boolean"}]]
		filters, _ = self.handler._resolve_query_filters(config, self.context, self.action)
		self.assertEqual(filters[0][2], 0)

	def test_nested_resolver_in_filters(self):
		# Complex resolver inside a filter
		config = {
			"filters": {
				"total": {
					"mode": "resolver",
					"config": {
						"kind": "math_formula",
						"field_a": "doc.limit_val",
						"math_op": "*",
						"field_b_type": "constant",
						"constant_b": 2,
					},
				}
			}
		}
		filters, _ = self.handler._resolve_query_filters(config, self.context, self.action)
		self.assertEqual(filters[0][2], 20.0)

	def test_interpolation_in_filters(self):
		config = {"filters": [["description", "like", "Status is {doc.status} for {vars.search_term}"]]}
		filters, _ = self.handler._resolve_query_filters(config, self.context, self.action)
		self.assertEqual(filters[0][2], "Status is Open for Flexi")

	@patch("frappe.get_list")
	def test_query_list_integration(self, mock_get_list):
		config = {
			"filters": {"status": {"mode": "variable", "path": "doc.status"}},
			"fields": ["name", "status"],
			"limit_type": "Custom Limit",
			"limit": 5,
		}
		self.handler._query_list("User", config, self.context, self.action, ignore_permissions=True)

		mock_get_list.assert_called_once()
		args = mock_get_list.call_args[1]
		self.assertEqual(args["doctype"], "User")
		self.assertEqual(args["filters"], [["status", "=", "Open"]])
		self.assertEqual(args["limit_page_length"], 5)
		self.assertEqual(args["fields"], ["name", "status"])

	def test_resolve_filters_with_context_edge_cases(self):
		# Test None filters
		self.assertIsNone(self.handler._resolve_filters_with_context(None, self.context, "test"))

		# Test plain values in list
		config_filters_list = ["direct_value", 123]
		resolved_list = self.handler._resolve_filters_with_context(config_filters_list, self.context, "test")
		self.assertEqual(resolved_list, ["direct_value", 123])

		# Test dictionary with no mode
		config_filters_dict = {"a": 1, "b": 2}
		resolved_dict = self.handler._resolve_filters_with_context(config_filters_dict, self.context, "test")
		self.assertEqual(resolved_dict, {"a": 1, "b": 2})

	def test_or_filters_resolution(self):
		config = {
			"filters": {"status": "Open"},
			"or_filters": [
				["priority", "=", {"mode": "static", "value": "High"}],
				{"field": "owner", "operator": "=", "value": "{doc.status}"},
			],
		}
		with patch("frappe.session", frappe._dict({"user": "admin@example.com"})):
			filters, or_filters = self.handler._resolve_query_filters(config, self.context, self.action)

			self.assertEqual(filters, [["status", "=", "Open"]])
			self.assertIn(["priority", "=", "High"], or_filters)
			self.assertIn(["owner", "=", "Open"], or_filters)

	@patch("frappe.desk.query_report.run")
	def test_query_report_structured_filters(self, mock_run):
		# Mock report execution with structured FlexValue filters
		config = {
			"report_name": "Sales Register",
			"filters": {
				"customer": {"mode": "static", "value": "Customer A"},
				"status": {"mode": "variable", "path": "doc.status"},
			}
		}
		mock_run.return_value = {"columns": [], "result": []}

		self.handler._query_report("Report", config, self.context, self.action, ignore_permissions=True)

		mock_run.assert_called_once_with(
			"Sales Register",
			filters={"customer": "Customer A", "status": "Open"}
		)
