# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.core.action_handlers.query_records import QueryRecordsHandler


class TestFetchRecordsNormalization(FrappeTestCase):
	"""
	Empirical Test Suite: Fetch Records UI Operator Normalization
	and Value Coercion in QueryRecordsHandler.
	"""

	def setUp(self):
		self.handler = QueryRecordsHandler()

	def test_01_ui_operator_normalization(self):
		"""Test operator conversions: starts with, ends with, Between, Timespan."""
		# starts with
		op, val = self.handler._normalize_single_filter_operator("starts with", "Test")
		self.assertEqual(op, "like")
		self.assertEqual(val, "Test%")

		# ends with
		op, val = self.handler._normalize_single_filter_operator("ends with", "End")
		self.assertEqual(op, "like")
		self.assertEqual(val, "%End")

		# Between
		op, val = self.handler._normalize_single_filter_operator("Between", ["2026-01-01", "2026-01-31"])
		self.assertEqual(op, "between")
		self.assertEqual(val, ["2026-01-01", "2026-01-31"])

		# Timespan
		op, val = self.handler._normalize_single_filter_operator("Timespan", "this month")
		self.assertEqual(op, "between")
		self.assertIsInstance(val, list)
		self.assertEqual(len(val), 2)

	def test_02_coerce_between_value_shapes(self):
		"""Test _coerce_between_value across lists, tuples, comma strings, and single strings."""
		# List / Tuple
		s, e = self.handler._coerce_between_value(["2026-01-01", "2026-01-31"])
		self.assertEqual((s, e), ("2026-01-01", "2026-01-31"))

		# Comma string
		s, e = self.handler._coerce_between_value("2026-02-01, 2026-02-28")
		self.assertEqual((s, e), ("2026-02-01", "2026-02-28"))

		# Single string fallback (treated as single-day range)
		s, e = self.handler._coerce_between_value("2026-03-01")
		self.assertEqual((s, e), ("2026-03-01", "2026-03-01"))

	def test_03_extract_filter_value_payload(self):
		"""Test extraction of value payloads from enhanced UI dictionaries."""
		# Plain value
		self.assertEqual(self.handler._extract_filter_value_payload("plain"), "plain")

		# Dictionary payload with boolean value_type
		payload_true = {"value": "Yes", "value_type": "boolean"}
		self.assertEqual(self.handler._extract_filter_value_payload(payload_true), 1)

		payload_false = {"value": "No", "value_type": "boolean"}
		self.assertEqual(self.handler._extract_filter_value_payload(payload_false), 0)

	def test_04_normalize_filters_for_backend_group_disambiguation(self):
		"""3-element items are recognized as filter leaves [field, op, val] vs logical groups [leaf1, 'or', leaf2]."""
		# Filter leaf of len 3: ['status', '=', 'Open']
		leaf_res = self.handler._normalize_filters_for_backend([["status", "=", "Open"]], "ToDo")
		self.assertEqual(leaf_res, [["status", "=", "Open"]])

		# Logical group of len 3: [['status', '=', 'Open'], 'or', ['status', '=', 'Closed']]
		tree_input = [
			["status", "=", "Open"],
			"or",
			["status", "=", "Closed"],
		]
		tree_res = self.handler._normalize_filters_for_backend(tree_input, "ToDo")
		self.assertEqual(tree_res, [["status", "=", "Open"], "or", ["status", "=", "Closed"]])
