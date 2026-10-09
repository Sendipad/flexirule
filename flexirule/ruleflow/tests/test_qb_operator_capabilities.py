# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

import uuid
from typing import ClassVar

import frappe
from frappe.tests.utils import FrappeTestCase


class TestQBOperatorCapabilities(FrappeTestCase):
	"""
	Empirical Test Suite: Native Operator Capabilities and Operand Behavior
	in frappe.qb.get_query() using the installed Rule DocType.
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
		prefix = f"_TEST_QB_OP_{cls._run_id}_"

		records = [
			{
				"rule_name": f"{prefix}RULE_A",
				"max_execution_time": 10,
				"description": "alpha_1",
			},
			{
				"rule_name": f"{prefix}RULE_B",
				"max_execution_time": 20,
				"description": "beta_2",
			},
			{
				"rule_name": f"{prefix}RULE_C",
				"max_execution_time": 30,
				"description": None,
			},
			{
				"rule_name": f"{prefix}RULE_D",
				"max_execution_time": 40,
				"description": "",
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

		cls.rule_a = records[0]["rule_name"]
		cls.rule_b = records[1]["rule_name"]
		cls.rule_c = records[2]["rule_name"]
		cls.rule_d = records[3]["rule_name"]
		cls.all_names = [cls.rule_a, cls.rule_b, cls.rule_c, cls.rule_d]

		frappe.db.commit()

	def test_01_all_six_comparison_operators(self):
		"""Explicitly test all six native comparison operators: =, !=, >, >=, <, <=."""
		base_filters = [["rule_name", "in", self.all_names]]

		# Equals
		r_eq = frappe.qb.get_query(
			"Rule",
			fields=["rule_name", "max_execution_time"],
			filters=[*base_filters, ["max_execution_time", "=", 10]],
		).run(as_dict=True)
		self.assertEqual({r["rule_name"] for r in r_eq}, {self.rule_a})

		# Not Equals
		r_neq = frappe.qb.get_query(
			"Rule",
			fields=["rule_name", "max_execution_time"],
			filters=[*base_filters, ["max_execution_time", "!=", 10]],
		).run(as_dict=True)
		self.assertEqual(
			{r["rule_name"] for r in r_neq},
			{self.rule_b, self.rule_c, self.rule_d},
		)

		# Greater Than
		r_gt = frappe.qb.get_query(
			"Rule",
			fields=["rule_name", "max_execution_time"],
			filters=[*base_filters, ["max_execution_time", ">", 20]],
		).run(as_dict=True)
		self.assertEqual({r["rule_name"] for r in r_gt}, {self.rule_c, self.rule_d})

		# Greater Than or Equal
		r_gte = frappe.qb.get_query(
			"Rule",
			fields=["rule_name", "max_execution_time"],
			filters=[*base_filters, ["max_execution_time", ">=", 20]],
		).run(as_dict=True)
		self.assertEqual(
			{r["rule_name"] for r in r_gte},
			{self.rule_b, self.rule_c, self.rule_d},
		)

		# Less Than
		r_lt = frappe.qb.get_query(
			"Rule",
			fields=["rule_name", "max_execution_time"],
			filters=[*base_filters, ["max_execution_time", "<", 20]],
		).run(as_dict=True)
		self.assertEqual({r["rule_name"] for r in r_lt}, {self.rule_a})

		# Less Than or Equal
		r_lte = frappe.qb.get_query(
			"Rule",
			fields=["rule_name", "max_execution_time"],
			filters=[*base_filters, ["max_execution_time", "<=", 20]],
		).run(as_dict=True)
		self.assertEqual({r["rule_name"] for r in r_lte}, {self.rule_a, self.rule_b})

	def test_02_pattern_matching_like_and_not_like(self):
		"""Test 'like' and 'not like' operators with % and _ wildcards."""
		base_filters = [["rule_name", "in", self.all_names]]

		# Direct caller-supplied wildcards
		res_like = frappe.qb.get_query(
			"Rule",
			fields=["rule_name", "description"],
			filters=[*base_filters, ["description", "like", "alpha%"]],
		).run(as_dict=True)
		self.assertEqual({r["rule_name"] for r in res_like}, {self.rule_a})

		# Plain string without wildcards performs exact match
		res_plain_like = frappe.qb.get_query(
			"Rule",
			fields=["rule_name", "description"],
			filters=[*base_filters, ["description", "like", "alpha_1"]],
		).run(as_dict=True)
		self.assertEqual({r["rule_name"] for r in res_plain_like}, {self.rule_a})

		# Single-character underscore wildcard (_)
		res_underscore = frappe.qb.get_query(
			"Rule",
			fields=["rule_name", "description"],
			filters=[*base_filters, ["description", "like", "alpha_1"]],
		).run(as_dict=True)
		self.assertEqual({r["rule_name"] for r in res_underscore}, {self.rule_a})

		# Not like excludes matching records; SQL NULL records (rule_c) are omitted due to SQL NULL tri-state logic
		res_not_like = frappe.qb.get_query(
			"Rule",
			fields=["rule_name", "description"],
			filters=[*base_filters, ["description", "not like", "alpha%"]],
		).run(as_dict=True)
		self.assertEqual({r["rule_name"] for r in res_not_like}, {self.rule_b, self.rule_d})

	def test_03_in_and_not_in_operators(self):
		"""Test 'in' and 'not in' with populated and empty sequences."""
		base_filters = [["rule_name", "in", self.all_names]]

		res_in = frappe.qb.get_query(
			"Rule",
			fields=["rule_name", "max_execution_time"],
			filters=[*base_filters, ["max_execution_time", "in", [10, 20]]],
		).run(as_dict=True)
		self.assertEqual({r["rule_name"] for r in res_in}, {self.rule_a, self.rule_b})

		res_not_in = frappe.qb.get_query(
			"Rule",
			fields=["rule_name", "max_execution_time"],
			filters=[*base_filters, ["max_execution_time", "not in", [10, 20]]],
		).run(as_dict=True)
		self.assertEqual({r["rule_name"] for r in res_not_in}, {self.rule_c, self.rule_d})

		# Empty sequence handling: converted to ('',) natively, returning 0 records
		res_empty_in = frappe.qb.get_query(
			"Rule",
			fields=["rule_name", "max_execution_time"],
			filters=[*base_filters, ["max_execution_time", "in", []]],
		).run(as_dict=True)
		self.assertEqual(len(res_empty_in), 0)

		# Comma-separated string input: func_in splits on comma natively
		comma_str = f"{self.rule_a},{self.rule_b}"
		res_comma_in = frappe.qb.get_query(
			"Rule",
			fields=["rule_name", "max_execution_time"],
			filters=[*base_filters, ["rule_name", "in", comma_str]],
		).run(as_dict=True)
		self.assertEqual({r["rule_name"] for r in res_comma_in}, {self.rule_a, self.rule_b})

	def test_04_is_set_and_is_not_set_null_vs_empty_string(self):
		"""Test 'is set' and 'is not set' behavior against both SQL NULL (None) and empty string ("")."""
		base_filters = [["rule_name", "in", self.all_names]]

		# 'is set' matches non-null and non-empty strings
		res_set = frappe.qb.get_query(
			"Rule",
			fields=["rule_name", "description"],
			filters=[*base_filters, ["description", "is", "set"]],
		).run(as_dict=True)
		self.assertEqual({r["rule_name"] for r in res_set}, {self.rule_a, self.rule_b})

		# 'is not set' matches BOTH SQL NULL (rule_c) AND empty string "" (rule_d)
		res_not_set = frappe.qb.get_query(
			"Rule",
			fields=["rule_name", "description"],
			filters=[*base_filters, ["description", "is", "not set"]],
		).run(as_dict=True)
		self.assertEqual({r["rule_name"] for r in res_not_set}, {self.rule_c, self.rule_d})

	def test_05_between_operator_numeric_boundaries(self):
		"""Test 'between' operator inclusive range boundaries."""
		base_filters = [["rule_name", "in", self.all_names]]

		res = frappe.qb.get_query(
			"Rule",
			fields=["rule_name", "max_execution_time"],
			filters=[*base_filters, ["max_execution_time", "between", [10, 20]]],
		).run(as_dict=True)
		self.assertEqual({r["rule_name"] for r in res}, {self.rule_a, self.rule_b})

	def test_06_unsupported_operator_error_stage(self):
		"""Unsupported operator string raises KeyError during OPERATOR_MAP lookup."""
		with self.assertRaises(KeyError):
			frappe.qb.get_query("Rule", filters=[["max_execution_time", "invalid_op", 10]]).run(as_dict=True)
