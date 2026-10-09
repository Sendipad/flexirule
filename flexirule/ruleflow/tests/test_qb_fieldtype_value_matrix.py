# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

import datetime
from typing import ClassVar

import frappe
from frappe.tests.utils import FrappeTestCase


class TestQBFieldtypeValueMatrix(FrappeTestCase):
	"""
	Empirical Test Suite: Fieldtype x Value Matrix
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
		frappe.db.delete("QB Matrix Parent")

		for dt in cls._created_doctypes:
			if frappe.db.exists("DocType", dt):
				frappe.delete_doc(dt, force=True, ignore_permissions=True)

		frappe.db.commit()
		super().tearDownClass()

	@classmethod
	def _setup_test_doctypes(cls):
		dt = "QB Matrix Parent"
		if not frappe.db.exists("DocType", dt):
			frappe.get_doc(
				{
					"doctype": "DocType",
					"name": dt,
					"module": "RuleFlow",
					"custom": 1,
					"fields": [
						{"fieldname": "data_field", "fieldtype": "Data", "label": "Data Field"},
						{
							"fieldname": "select_field",
							"fieldtype": "Select",
							"options": "Option A\nOption B",
							"label": "Select Field",
						},
						{"fieldname": "check_field", "fieldtype": "Check", "label": "Check Field"},
						{"fieldname": "int_field", "fieldtype": "Int", "label": "Int Field"},
						{"fieldname": "float_field", "fieldtype": "Float", "label": "Float Field"},
						{"fieldname": "currency_field", "fieldtype": "Currency", "label": "Currency Field"},
						{"fieldname": "date_field", "fieldtype": "Date", "label": "Date Field"},
						{"fieldname": "datetime_field", "fieldtype": "Datetime", "label": "Datetime Field"},
					],
				}
			).insert(ignore_permissions=True)
			cls._created_doctypes.append(dt)

		frappe.db.commit()

	@classmethod
	def _setup_test_records(cls):
		frappe.db.delete("QB Matrix Parent")

		cls.m1 = frappe.get_doc(
			{
				"doctype": "QB Matrix Parent",
				"data_field": "Sample Data",
				"select_field": "Option A",
				"check_field": 1,
				"int_field": 42,
				"float_field": 3.14159,
				"currency_field": 99.99,
				"date_field": "2026-03-01",
				"datetime_field": "2026-03-01 12:00:00",
			}
		).insert(ignore_permissions=True)

		cls.m2 = frappe.get_doc(
			{
				"doctype": "QB Matrix Parent",
				"data_field": None,
				"select_field": "Option B",
				"check_field": 0,
				"int_field": 0,
				"float_field": 0.0,
				"currency_field": 0.00,
				"date_field": "2026-03-15",
				"datetime_field": "2026-03-15 18:30:00",
			}
		).insert(ignore_permissions=True)

		frappe.db.commit()

	def test_01_check_field_boolean_and_numeric_coercion(self):
		"""Check fields convert boolean True/False to 1/0."""
		res_true = frappe.qb.get_query("QB Matrix Parent", filters=[["check_field", "=", True]]).run(
			as_dict=True
		)
		self.assertEqual(len(res_true), 1)
		self.assertEqual(res_true[0]["name"], self.m1.name)

		res_false = frappe.qb.get_query("QB Matrix Parent", filters=[["check_field", "=", False]]).run(
			as_dict=True
		)
		self.assertEqual(len(res_false), 1)
		self.assertEqual(res_false[0]["name"], self.m2.name)

	def test_02_numeric_and_currency_fields(self):
		"""Int, Float, and Currency comparisons."""
		res_int = frappe.qb.get_query("QB Matrix Parent", filters=[["int_field", ">", 10]]).run(as_dict=True)
		self.assertEqual(len(res_int), 1)

		res_float = frappe.qb.get_query("QB Matrix Parent", filters=[["float_field", ">", 3.0]]).run(
			as_dict=True
		)
		self.assertEqual(len(res_float), 1)

		res_curr = frappe.qb.get_query("QB Matrix Parent", filters=[["currency_field", "=", 99.99]]).run(
			as_dict=True
		)
		self.assertEqual(len(res_curr), 1)

	def test_03_date_and_datetime_iso_and_python_objects(self):
		"""ISO date strings and Python date/datetime objects."""
		# ISO string
		res_date_str = frappe.qb.get_query(
			"QB Matrix Parent", filters=[["date_field", "=", "2026-03-01"]]
		).run(as_dict=True)
		self.assertEqual(len(res_date_str), 1)

		# Python datetime.date
		d_obj = datetime.date(2026, 3, 1)
		res_date_obj = frappe.qb.get_query("QB Matrix Parent", filters=[["date_field", "=", d_obj]]).run(
			as_dict=True
		)
		self.assertEqual(len(res_date_obj), 1)

		# Datetime string
		res_dt_str = frappe.qb.get_query(
			"QB Matrix Parent", filters=[["datetime_field", ">=", "2026-03-15 00:00:00"]]
		).run(as_dict=True)
		self.assertEqual(len(res_dt_str), 1)
		self.assertEqual(res_dt_str[0]["name"], self.m2.name)
