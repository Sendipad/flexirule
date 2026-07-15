# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

import unittest
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.core.action_handlers.query_records import QueryRecordsHandler


class TestQueryReportSerialization(FrappeTestCase):
	def setUp(self):
		self.handler = QueryRecordsHandler()
		self.context = {
			"doc": frappe._dict({"status": "Open", "company": "Test Company"}),
			"vars": {"search_term": "Flexi", "cost_centers": ["Cost Center A", "Cost Center B"]},
		}
		self.action = frappe._dict({"name": "ACT001", "label": "TestQueryReport", "config": "{}"})

	def test_nested_primitive_resolution_with_flex_value(self):
		# Standard static FlexValueControl object representation
		static_val = {"mode": "static", "value": "30, 60, 90, 120"}
		res = self.handler._resolve_nested_primitive_value(static_val)
		self.assertEqual(res, "30, 60, 90, 120")

		# MultiSelectList containing FlexValueControl representations
		list_val = [
			{"mode": "static", "value": "Cost Center A"},
			{"mode": "static", "value": "Cost Center B"}
		]
		res = self.handler._resolve_nested_primitive_value(list_val)
		self.assertEqual(res, ["Cost Center A", "Cost Center B"])

	@patch("frappe.desk.query_report.run")
	def test_query_report_serialization(self, mock_run_report):
		config = {
			"report_name": "Accounts Receivable",
			"filters": {
				"company": {"mode": "variable", "path": "doc.company"},
				"range": {"mode": "static", "value": "30,60,90,120"},
				"cost_center": [
					{"mode": "variable", "path": "vars.cost_centers"}
				]
			}
		}

		mock_run_report.return_value = {"columns": [], "result": []}

		self.handler._query_report(
			reference_doctype="Report",
			config=config,
			context=self.context,
			action=self.action,
			ignore_permissions=True
		)

		mock_run_report.assert_called_once()
		args, kwargs = mock_run_report.call_args
		self.assertEqual(args[0], "Accounts Receivable")
		filters = kwargs["filters"]

		# Confirm all FlexValueControl dictionary structures have been resolved down to native primitives!
		self.assertEqual(filters["company"], "Test Company")
		self.assertEqual(filters["range"], "30,60,90,120")
		self.assertEqual(filters["cost_center"], ["Cost Center A", "Cost Center B"])
