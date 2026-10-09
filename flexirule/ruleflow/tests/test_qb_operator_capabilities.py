# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

from typing import ClassVar

import frappe
from frappe.tests.utils import FrappeTestCase


class TestQBOperatorCapabilities(FrappeTestCase):
	"""
	Empirical Test Suite: Native Operator Capabilities and Operand Behavior
	in frappe.qb.get_query().
	"""

	_created_doctypes: ClassVar[list[str]] = []

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls._setup_test_doctypes()
		cls._setup_test_records()

	@classmethod
	def tearDownClass(cls):
		frappe.db.delete("QB Op Parent")

		for dt in cls._created_doctypes:
			if frappe.db.exists("DocType", dt):
				frappe.delete_doc(dt, force=True, ignore_permissions=True)

		frappe.db.commit()
		super().tearDownClass()

	@classmethod
	def _setup_test_doctypes(cls):
		dt = "QB Op Parent"
		if not frappe.db.exists("DocType", dt):
			frappe.get_doc(
				{
					"doctype": "DocType",
					"name": dt,
					"module": "RuleFlow",
					"custom": 1,
					"fields": [
						{"fieldname": "code", "fieldtype": "Data", "label": "Code"},
						{"fieldname": "val", "fieldtype": "Int", "label": "Value"},
						{"fieldname": "notes", "fieldtype": "Data", "label": "Notes"},
					],
				}
			).insert(ignore_permissions=True)
			cls._created_doctypes.append(dt)

		frappe.db.commit()

	@classmethod
	def _setup_test_records(cls):
		frappe.db.delete("QB Op Parent")

		cls.r1 = frappe.get_doc(
			{
				"doctype": "QB Op Parent",
				"code": "CODE_A",
				"val": 10,
				"notes": "alpha_1",
			}
		).insert(ignore_permissions=True)

		cls.r2 = frappe.get_doc(
			{
				"doctype": "QB Op Parent",
				"code": "CODE_B",
				"val": 20,
				"notes": "beta_2",
			}
		).insert(ignore_permissions=True)

		cls.r3 = frappe.get_doc(
			{
				"doctype": "QB Op Parent",
				"code": "CODE_C",
				"val": 30,
				"notes": None,
			}
		).insert(ignore_permissions=True)

		cls.r4 = frappe.get_doc(
			{
				"doctype": "QB Op Parent",
				"code": "CODE_D",
				"val": 40,
				"notes": "",
			}
		).insert(ignore_permissions=True)

		frappe.db.commit()

	def test_01_all_six_comparison_operators(self):
		"""Explicitly test all six native comparison operators: =, !=, >, >=, <, <=."""
		# Equals
		r_eq = frappe.qb.get_query("QB Op Parent", fields=["code", "val"], filters=[["val", "=", 10]]).run(
			as_dict=True
		)
		self.assertEqual({r["code"] for r in r_eq}, {"CODE_A"})

		# Not Equals
		r_neq = frappe.qb.get_query("QB Op Parent", fields=["code", "val"], filters=[["val", "!=", 10]]).run(
			as_dict=True
		)
		self.assertEqual({r["code"] for r in r_neq}, {"CODE_B", "CODE_C", "CODE_D"})

		# Greater Than
		r_gt = frappe.qb.get_query("QB Op Parent", fields=["code", "val"], filters=[["val", ">", 20]]).run(
			as_dict=True
		)
		self.assertEqual({r["code"] for r in r_gt}, {"CODE_C", "CODE_D"})

		# Greater Than or Equal
		r_gte = frappe.qb.get_query("QB Op Parent", fields=["code", "val"], filters=[["val", ">=", 20]]).run(
			as_dict=True
		)
		self.assertEqual({r["code"] for r in r_gte}, {"CODE_B", "CODE_C", "CODE_D"})

		# Less Than
		r_lt = frappe.qb.get_query("QB Op Parent", fields=["code", "val"], filters=[["val", "<", 20]]).run(
			as_dict=True
		)
		self.assertEqual({r["code"] for r in r_lt}, {"CODE_A"})

		# Less Than or Equal
		r_lte = frappe.qb.get_query("QB Op Parent", fields=["code", "val"], filters=[["val", "<=", 20]]).run(
			as_dict=True
		)
		self.assertEqual({r["code"] for r in r_lte}, {"CODE_A", "CODE_B"})

	def test_02_pattern_matching_like_and_not_like(self):
		"""Test 'like' and 'not like' operators with % and _ wildcards."""
		res_like = frappe.qb.get_query(
			"QB Op Parent", fields=["code", "notes"], filters=[["notes", "like", "alpha%"]]
		).run(as_dict=True)
		self.assertEqual({r["code"] for r in res_like}, {"CODE_A"})

		res_not_like = frappe.qb.get_query(
			"QB Op Parent", fields=["code", "notes"], filters=[["notes", "not like", "alpha%"]]
		).run(as_dict=True)
		self.assertEqual({r["code"] for r in res_not_like}, {"CODE_B", "CODE_D"})

	def test_03_in_and_not_in_operators(self):
		"""Test 'in' and 'not in' with populated and empty sequences."""
		res_in = frappe.qb.get_query(
			"QB Op Parent", fields=["code", "val"], filters=[["val", "in", [10, 20]]]
		).run(as_dict=True)
		self.assertEqual({r["code"] for r in res_in}, {"CODE_A", "CODE_B"})

		res_not_in = frappe.qb.get_query(
			"QB Op Parent", fields=["code", "val"], filters=[["val", "not in", [10, 20]]]
		).run(as_dict=True)
		self.assertEqual({r["code"] for r in res_not_in}, {"CODE_C", "CODE_D"})

		# Empty sequence handling
		res_empty_in = frappe.qb.get_query(
			"QB Op Parent", fields=["code", "val"], filters=[["val", "in", []]]
		).run(as_dict=True)
		self.assertEqual(len(res_empty_in), 0)

	def test_04_is_set_and_is_not_set_null_vs_empty_string(self):
		"""Test 'is set' and 'is not set' behavior against both SQL NULL (None) and empty string ("")."""
		# 'is set' matches non-null and non-empty strings
		res_set = frappe.qb.get_query(
			"QB Op Parent", fields=["code", "notes"], filters=[["notes", "is", "set"]]
		).run(as_dict=True)
		self.assertEqual({r["code"] for r in res_set}, {"CODE_A", "CODE_B"})

		# 'is not set' matches BOTH SQL NULL (CODE_C) AND empty string "" (CODE_D)
		res_not_set = frappe.qb.get_query(
			"QB Op Parent", fields=["code", "notes"], filters=[["notes", "is", "not set"]]
		).run(as_dict=True)
		self.assertEqual({r["code"] for r in res_not_set}, {"CODE_C", "CODE_D"})

	def test_05_between_operator_numeric_boundaries(self):
		"""Test 'between' operator inclusive range boundaries."""
		res = frappe.qb.get_query(
			"QB Op Parent", fields=["code", "val"], filters=[["val", "between", [10, 20]]]
		).run(as_dict=True)
		self.assertEqual({r["code"] for r in res}, {"CODE_A", "CODE_B"})

	def test_06_unsupported_operator_error_stage(self):
		"""Unsupported operator string raises KeyError during OPERATOR_MAP lookup."""
		with self.assertRaises(KeyError):
			frappe.qb.get_query("QB Op Parent", filters=[["val", "invalid_op", 10]]).run(as_dict=True)
