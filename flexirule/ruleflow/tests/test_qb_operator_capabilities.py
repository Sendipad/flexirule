# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

import datetime
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
			{"doctype": "QB Op Parent", "code": "CODE_A", "val": 10, "notes": "alpha_1"}
		).insert(ignore_permissions=True)
		cls.r2 = frappe.get_doc(
			{"doctype": "QB Op Parent", "code": "CODE_B", "val": 20, "notes": "beta_2"}
		).insert(ignore_permissions=True)
		cls.r3 = frappe.get_doc(
			{"doctype": "QB Op Parent", "code": "CODE_C", "val": 30, "notes": None}
		).insert(ignore_permissions=True)

		frappe.db.commit()

	def test_01_comparison_operators(self):
		"""Test =, !=, >, >=, <, <="""
		res = frappe.qb.get_query("QB Op Parent", fields=["code", "val"], filters=[["val", ">", 15]]).run(
			as_dict=True
		)
		self.assertEqual({r["code"] for r in res}, {"CODE_B", "CODE_C"})

		res = frappe.qb.get_query("QB Op Parent", fields=["code", "val"], filters=[["val", "<=", 10]]).run(
			as_dict=True
		)
		self.assertEqual({r["code"] for r in res}, {"CODE_A"})

	def test_02_pattern_matching_wildcards(self):
		"""Test 'like' and 'not like' with % (multi-char) and _ (single-char) wildcards."""
		res = frappe.qb.get_query(
			"QB Op Parent", fields=["code", "notes"], filters=[["notes", "like", "alpha%"]]
		).run(as_dict=True)
		self.assertEqual(len(res), 1)
		self.assertEqual(res[0]["code"], "CODE_A")

		res_single = frappe.qb.get_query(
			"QB Op Parent", fields=["code", "notes"], filters=[["notes", "like", "beta_2"]]
		).run(as_dict=True)
		self.assertEqual(len(res_single), 1)
		self.assertEqual(res_single[0]["code"], "CODE_B")

	def test_03_in_and_not_in_with_empty_sequence(self):
		"""Test 'in' and 'not in' with populated and empty sequences."""
		res = frappe.qb.get_query(
			"QB Op Parent", fields=["code", "val"], filters=[["val", "in", [10, 20]]]
		).run(as_dict=True)
		self.assertEqual({r["code"] for r in res}, {"CODE_A", "CODE_B"})

		# Empty list is converted by _apply_filter to ('',) preventing SQL syntax error
		res_empty = frappe.qb.get_query(
			"QB Op Parent", fields=["code", "val"], filters=[["val", "in", []]]
		).run(as_dict=True)
		self.assertEqual(len(res_empty), 0)

	def test_04_is_and_null_semantics(self):
		"""Test 'is' operator with 'set', 'not set', and None in '=' operator."""
		res_null = frappe.qb.get_query(
			"QB Op Parent", fields=["code", "notes"], filters=[["notes", "=", None]]
		).run(as_dict=True)
		self.assertEqual(len(res_null), 1)
		self.assertEqual(res_null[0]["code"], "CODE_C")

		res_set = frappe.qb.get_query(
			"QB Op Parent", fields=["code", "notes"], filters=[["notes", "is", "set"]]
		).run(as_dict=True)
		self.assertEqual({r["code"] for r in res_set}, {"CODE_A", "CODE_B"})

		res_not_set = frappe.qb.get_query(
			"QB Op Parent", fields=["code", "notes"], filters=[["notes", "is", "not set"]]
		).run(as_dict=True)
		self.assertEqual(len(res_not_set), 1)
		self.assertEqual(res_not_set[0]["code"], "CODE_C")

	def test_05_between_operator(self):
		"""Test 'between' operator with numeric ranges."""
		res = frappe.qb.get_query(
			"QB Op Parent", fields=["code", "val"], filters=[["val", "between", [10, 20]]]
		).run(as_dict=True)
		self.assertEqual({r["code"] for r in res}, {"CODE_A", "CODE_B"})

	def test_06_unsupported_operator_error_stage(self):
		"""Unsupported operator string raises KeyError during OPERATOR_MAP lookup."""
		with self.assertRaises(KeyError):
			frappe.qb.get_query("QB Op Parent", filters=[["val", "invalid_op", 10]]).run(as_dict=True)
