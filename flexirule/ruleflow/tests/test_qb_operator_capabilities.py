# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

from typing import ClassVar

import frappe
from frappe.tests.utils import FrappeTestCase


class TestQBOperatorCapabilities(FrappeTestCase):
	"""
	Empirical Test Suite: Native Operator Capabilities and Operand Behavior
	in frappe.qb.get_query() using the installed Rule DocType.
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
				"rule_name": "_TEST_QB_OP_RULE_A",
				"max_execution_time": 10,
				"description": "alpha_1",
			},
			{
				"rule_name": "_TEST_QB_OP_RULE_B",
				"max_execution_time": 20,
				"description": "beta_2",
			},
			{
				"rule_name": "_TEST_QB_OP_RULE_C",
				"max_execution_time": 30,
				"description": None,
			},
			{
				"rule_name": "_TEST_QB_OP_RULE_D",
				"max_execution_time": 40,
				"description": "",
			},
		]

		for data in records:
			if frappe.db.exists("Rule", data["rule_name"]):
				frappe.delete_doc("Rule", data["rule_name"], force=True, ignore_permissions=True)

			doc = frappe.get_doc(
				{
					"doctype": "Rule",
					"rule_name": data["rule_name"],
					"max_execution_time": data["max_execution_time"],
					"description": data["description"],
					"priority": "10",
					"trigger_type": "DocType Event",
					"document_type": "User",
					"trigger_event": "Validate",
					"execution_mode": "Synchronous",
				}
			).insert(ignore_permissions=True)

			cls._created_records.append(("Rule", doc.name))

		frappe.db.commit()

	def test_01_all_six_comparison_operators(self):
		"""Explicitly test all six native comparison operators: =, !=, >, >=, <, <=."""
		base_filters = [["rule_name", "like", "_TEST_QB_OP_RULE_%"]]

		# Equals
		r_eq = frappe.qb.get_query(
			"Rule",
			fields=["rule_name", "max_execution_time"],
			filters=[*base_filters, ["max_execution_time", "=", 10]],
		).run(as_dict=True)
		self.assertEqual({r["rule_name"] for r in r_eq}, {"_TEST_QB_OP_RULE_A"})

		# Not Equals
		r_neq = frappe.qb.get_query(
			"Rule",
			fields=["rule_name", "max_execution_time"],
			filters=[*base_filters, ["max_execution_time", "!=", 10]],
		).run(as_dict=True)
		self.assertEqual(
			{r["rule_name"] for r in r_neq},
			{"_TEST_QB_OP_RULE_B", "_TEST_QB_OP_RULE_C", "_TEST_QB_OP_RULE_D"},
		)

		# Greater Than
		r_gt = frappe.qb.get_query(
			"Rule",
			fields=["rule_name", "max_execution_time"],
			filters=[*base_filters, ["max_execution_time", ">", 20]],
		).run(as_dict=True)
		self.assertEqual({r["rule_name"] for r in r_gt}, {"_TEST_QB_OP_RULE_C", "_TEST_QB_OP_RULE_D"})

		# Greater Than or Equal
		r_gte = frappe.qb.get_query(
			"Rule",
			fields=["rule_name", "max_execution_time"],
			filters=[*base_filters, ["max_execution_time", ">=", 20]],
		).run(as_dict=True)
		self.assertEqual(
			{r["rule_name"] for r in r_gte},
			{"_TEST_QB_OP_RULE_B", "_TEST_QB_OP_RULE_C", "_TEST_QB_OP_RULE_D"},
		)

		# Less Than
		r_lt = frappe.qb.get_query(
			"Rule",
			fields=["rule_name", "max_execution_time"],
			filters=[*base_filters, ["max_execution_time", "<", 20]],
		).run(as_dict=True)
		self.assertEqual({r["rule_name"] for r in r_lt}, {"_TEST_QB_OP_RULE_A"})

		# Less Than or Equal
		r_lte = frappe.qb.get_query(
			"Rule",
			fields=["rule_name", "max_execution_time"],
			filters=[*base_filters, ["max_execution_time", "<=", 20]],
		).run(as_dict=True)
		self.assertEqual({r["rule_name"] for r in r_lte}, {"_TEST_QB_OP_RULE_A", "_TEST_QB_OP_RULE_B"})

	def test_02_pattern_matching_like_and_not_like(self):
		"""Test 'like' and 'not like' operators with % and _ wildcards."""
		base_filters = [["rule_name", "like", "_TEST_QB_OP_RULE_%"]]

		# Direct caller-supplied wildcards
		res_like = frappe.qb.get_query(
			"Rule",
			fields=["rule_name", "description"],
			filters=[*base_filters, ["description", "like", "alpha%"]],
		).run(as_dict=True)
		self.assertEqual({r["rule_name"] for r in res_like}, {"_TEST_QB_OP_RULE_A"})

		# Plain string without wildcards performs exact match
		res_plain_like = frappe.qb.get_query(
			"Rule",
			fields=["rule_name", "description"],
			filters=[*base_filters, ["description", "like", "alpha_1"]],
		).run(as_dict=True)
		self.assertEqual({r["rule_name"] for r in res_plain_like}, {"_TEST_QB_OP_RULE_A"})

		# Single-character underscore wildcard (_)
		res_underscore = frappe.qb.get_query(
			"Rule",
			fields=["rule_name", "description"],
			filters=[*base_filters, ["description", "like", "alpha_1"]],
		).run(as_dict=True)
		self.assertEqual({r["rule_name"] for r in res_underscore}, {"_TEST_QB_OP_RULE_A"})

		# Not like excludes matching records; SQL NULL records (_TEST_QB_OP_RULE_C) are omitted due to SQL NULL tri-state logic
		res_not_like = frappe.qb.get_query(
			"Rule",
			fields=["rule_name", "description"],
			filters=[*base_filters, ["description", "not like", "alpha%"]],
		).run(as_dict=True)
		self.assertEqual({r["rule_name"] for r in res_not_like}, {"_TEST_QB_OP_RULE_B", "_TEST_QB_OP_RULE_D"})

	def test_03_in_and_not_in_operators(self):
		"""Test 'in' and 'not in' with populated and empty sequences."""
		base_filters = [["rule_name", "like", "_TEST_QB_OP_RULE_%"]]

		res_in = frappe.qb.get_query(
			"Rule",
			fields=["rule_name", "max_execution_time"],
			filters=[*base_filters, ["max_execution_time", "in", [10, 20]]],
		).run(as_dict=True)
		self.assertEqual({r["rule_name"] for r in res_in}, {"_TEST_QB_OP_RULE_A", "_TEST_QB_OP_RULE_B"})

		res_not_in = frappe.qb.get_query(
			"Rule",
			fields=["rule_name", "max_execution_time"],
			filters=[*base_filters, ["max_execution_time", "not in", [10, 20]]],
		).run(as_dict=True)
		self.assertEqual({r["rule_name"] for r in res_not_in}, {"_TEST_QB_OP_RULE_C", "_TEST_QB_OP_RULE_D"})

		# Empty sequence handling: converted to ('',) natively, returning 0 records
		res_empty_in = frappe.qb.get_query(
			"Rule",
			fields=["rule_name", "max_execution_time"],
			filters=[*base_filters, ["max_execution_time", "in", []]],
		).run(as_dict=True)
		self.assertEqual(len(res_empty_in), 0)

		# Comma-separated string input: func_in splits on comma natively
		res_comma_in = frappe.qb.get_query(
			"Rule",
			fields=["rule_name", "max_execution_time"],
			filters=[*base_filters, ["rule_name", "in", "_TEST_QB_OP_RULE_A,_TEST_QB_OP_RULE_B"]],
		).run(as_dict=True)
		self.assertEqual(
			{r["rule_name"] for r in res_comma_in},
			{"_TEST_QB_OP_RULE_A", "_TEST_QB_OP_RULE_B"},
		)

	def test_04_is_set_and_is_not_set_null_vs_empty_string(self):
		"""Test 'is set' and 'is not set' behavior against both SQL NULL (None) and empty string ("")."""
		base_filters = [["rule_name", "like", "_TEST_QB_OP_RULE_%"]]

		# 'is set' matches non-null and non-empty strings
		res_set = frappe.qb.get_query(
			"Rule",
			fields=["rule_name", "description"],
			filters=[*base_filters, ["description", "is", "set"]],
		).run(as_dict=True)
		self.assertEqual({r["rule_name"] for r in res_set}, {"_TEST_QB_OP_RULE_A", "_TEST_QB_OP_RULE_B"})

		# 'is not set' matches BOTH SQL NULL (_TEST_QB_OP_RULE_C) AND empty string "" (_TEST_QB_OP_RULE_D)
		res_not_set = frappe.qb.get_query(
			"Rule",
			fields=["rule_name", "description"],
			filters=[*base_filters, ["description", "is", "not set"]],
		).run(as_dict=True)
		self.assertEqual(
			{r["rule_name"] for r in res_not_set},
			{"_TEST_QB_OP_RULE_C", "_TEST_QB_OP_RULE_D"},
		)

	def test_05_between_operator_numeric_boundaries(self):
		"""Test 'between' operator inclusive range boundaries."""
		base_filters = [["rule_name", "like", "_TEST_QB_OP_RULE_%"]]

		res = frappe.qb.get_query(
			"Rule",
			fields=["rule_name", "max_execution_time"],
			filters=[*base_filters, ["max_execution_time", "between", [10, 20]]],
		).run(as_dict=True)
		self.assertEqual({r["rule_name"] for r in res}, {"_TEST_QB_OP_RULE_A", "_TEST_QB_OP_RULE_B"})

	def test_06_unsupported_operator_error_stage(self):
		"""Unsupported operator string raises KeyError during OPERATOR_MAP lookup."""
		with self.assertRaises(KeyError):
			frappe.qb.get_query("Rule", filters=[["max_execution_time", "invalid_op", 10]]).run(as_dict=True)
