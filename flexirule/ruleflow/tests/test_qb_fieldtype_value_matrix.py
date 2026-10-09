# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

import datetime
import uuid
from typing import ClassVar

import frappe
from frappe.tests.utils import FrappeTestCase


class TestQBFieldtypeValueMatrix(FrappeTestCase):
	"""
	Empirical Test Suite: Fieldtype x Value Matrix
	in frappe.qb.get_query().

	Reuses installed DocTypes (Rule, Data Review Task) for Data, Select, Check,
	Int, Float, and Datetime fields, while maintaining a minimal dedicated fixture
	for missing Date & Currency fieldtypes.
	"""

	_created_doctypes: ClassVar[list[str]] = []
	_created_records: ClassVar[list[tuple[str, str]]] = []
	_run_id: ClassVar[str] = ""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls._created_doctypes = []
		cls._created_records = []
		cls._run_id = uuid.uuid4().hex[:8].upper()
		cls._setup_test_doctypes()
		cls._setup_test_records()

	@classmethod
	def tearDownClass(cls):
		for doctype, docname in reversed(cls._created_records):
			if frappe.db.exists(doctype, docname):
				frappe.delete_doc(doctype, docname, force=True, ignore_permissions=True)

		cls._created_records.clear()

		for dt in cls._created_doctypes:
			if frappe.db.exists("DocType", dt):
				frappe.delete_doc(dt, force=True, ignore_permissions=True)

		cls._created_doctypes.clear()

		frappe.db.commit()
		super().tearDownClass()

	@classmethod
	def _setup_test_doctypes(cls):
		dt = f"QB Matrix Temp {cls._run_id}"
		if frappe.db.exists("DocType", dt):
			raise RuntimeError(f"Unexpected pre-existing DocType: {dt}")

		frappe.get_doc(
			{
				"doctype": "DocType",
				"name": dt,
				"module": "RuleFlow",
				"custom": 1,
				"fields": [
					{"fieldname": "code", "fieldtype": "Data", "label": "Code", "reqd": 1},
					{"fieldname": "currency_field", "fieldtype": "Currency", "label": "Currency Field"},
					{"fieldname": "date_field", "fieldtype": "Date", "label": "Date Field"},
				],
			}
		).insert(ignore_permissions=True)
		cls._created_doctypes.append(dt)
		cls.temporal_doctype = dt

		frappe.db.commit()

	@classmethod
	def _setup_test_records(cls):
		prefix = f"_TEST_QB_MAT_{cls._run_id}_"

		# 1. Setup Rule records for Data, Check, Int, and Select testing
		rules: list[dict[str, object]] = [
			{
				"rule_name": f"{prefix}RULE_1",
				"is_active": 1,
				"priority": "10",
				"max_execution_time": 42,
				"description": "Sample Data",
			},
			{
				"rule_name": f"{prefix}RULE_2",
				"is_active": 0,
				"priority": "1",
				"max_execution_time": 0,
				"description": None,
			},
			{
				"rule_name": f"{prefix}RULE_3",
				"is_active": 1,
				"priority": "5",
				"max_execution_time": -10,
				"description": "Boundary Test",
			},
		]

		for data in rules:
			rule_name = str(data["rule_name"])
			if frappe.db.exists("Rule", rule_name):
				raise RuntimeError(f"Unexpected pre-existing Rule record: {rule_name}")

			doc = frappe.get_doc(
				{
					"doctype": "Rule",
					"rule_name": rule_name,
					"is_active": data["is_active"],
					"priority": data["priority"],
					"max_execution_time": data["max_execution_time"],
					"description": data["description"],
					"trigger_type": "DocType Event",
					"document_type": "User",
					"trigger_event": "Validate",
					"execution_mode": "Synchronous",
				}
			).insert(ignore_permissions=True)
			cls._created_records.append(("Rule", doc.name))

		cls.rule1_name = str(rules[0]["rule_name"])
		cls.rule2_name = str(rules[1]["rule_name"])
		cls.rule3_name = str(rules[2]["rule_name"])
		cls.rule_names = [cls.rule1_name, cls.rule2_name, cls.rule3_name]

		# 2. Setup Data Review Task records for Datetime testing
		tasks: list[dict[str, str]] = [
			{
				"source_doctype": "User",
				"source_document": "Administrator",
				"task_type": "Duplicate Review",
				"priority": "High",
				"resolved_on": "2026-03-01 12:00:00",
			},
			{
				"source_doctype": "User",
				"source_document": "Administrator",
				"task_type": "Data Quality",
				"priority": "Low",
				"resolved_on": "2026-03-15 18:30:00",
			},
			{
				"source_doctype": "User",
				"source_document": "Administrator",
				"task_type": "Merge Request",
				"priority": "Critical",
				"resolved_on": "2026-03-31 23:59:59.999999",
			},
		]

		for task_data in tasks:
			task_doc = frappe.get_doc(
				{
					"doctype": "Data Review Task",
					"source_doctype": task_data["source_doctype"],
					"source_document": task_data["source_document"],
					"task_type": task_data["task_type"],
					"priority": task_data["priority"],
					"resolved_on": task_data["resolved_on"],
					"status": "Open",
				}
			).insert(ignore_permissions=True)
			cls._created_records.append(("Data Review Task", task_doc.name))

		cls.task1_name = cls._created_records[-3][1]
		cls.task2_name = cls._created_records[-2][1]
		cls.task3_name = cls._created_records[-1][1]

		# 3. Setup QB Matrix Temporal records for Date and Currency testing
		temporals: list[dict[str, object]] = [
			{"code": f"{prefix}T1", "currency_field": 99.99, "date_field": "2026-03-01"},
			{"code": f"{prefix}T2", "currency_field": 0.00, "date_field": "2026-03-15"},
			{"code": f"{prefix}T3", "currency_field": 50.00, "date_field": "2026-03-31"},
		]

		for temp_data in temporals:
			temp_doc = frappe.get_doc(
				{
					"doctype": cls.temporal_doctype,
					"code": temp_data["code"],
					"currency_field": temp_data["currency_field"],
					"date_field": temp_data["date_field"],
				}
			).insert(ignore_permissions=True)
			cls._created_records.append((cls.temporal_doctype, temp_doc.name))

		cls.temp1_name = cls._created_records[-3][1]
		cls.temp2_name = cls._created_records[-2][1]
		cls.temp3_name = cls._created_records[-1][1]
		cls.temp_codes = [str(t["code"]) for t in temporals]

		frappe.db.commit()

	def test_01_check_field_boolean_and_numeric_coercion(self):
		"""Check fields convert boolean True/False to 1/0 on Rule.is_active."""
		base_filters = [["rule_name", "in", self.rule_names]]

		res_true = frappe.qb.get_query("Rule", filters=[*base_filters, ["is_active", "=", True]]).run(
			as_dict=True
		)
		self.assertEqual({r["name"] for r in res_true}, {self.rule1_name, self.rule3_name})

		res_false = frappe.qb.get_query("Rule", filters=[*base_filters, ["is_active", "=", False]]).run(
			as_dict=True
		)
		self.assertEqual({r["name"] for r in res_false}, {self.rule2_name})

		# Native integer 1 / 0
		res_int1 = frappe.qb.get_query("Rule", filters=[*base_filters, ["is_active", "=", 1]]).run(
			as_dict=True
		)
		self.assertEqual({r["name"] for r in res_int1}, {self.rule1_name, self.rule3_name})

		# Numeric string '1' / '0'
		res_str1 = frappe.qb.get_query("Rule", filters=[*base_filters, ["is_active", "=", "1"]]).run(
			as_dict=True
		)
		self.assertEqual({r["name"] for r in res_str1}, {self.rule1_name, self.rule3_name})

	def test_02_numeric_and_currency_fields(self):
		"""Int and Currency comparisons across native and string representations."""
		base_filters = [["rule_name", "in", self.rule_names]]

		# Native Int comparison on Rule.max_execution_time
		res_int = frappe.qb.get_query("Rule", filters=[*base_filters, ["max_execution_time", ">", 10]]).run(
			as_dict=True
		)
		self.assertEqual({r["name"] for r in res_int}, {self.rule1_name})

		# Numeric string integer comparison
		res_int_str = frappe.qb.get_query(
			"Rule", filters=[*base_filters, ["max_execution_time", "=", "42"]]
		).run(as_dict=True)
		self.assertEqual({r["name"] for r in res_int_str}, {self.rule1_name})

		# Negative integer boundary
		res_neg_int = frappe.qb.get_query(
			"Rule", filters=[*base_filters, ["max_execution_time", "<", 0]]
		).run(as_dict=True)
		self.assertEqual({r["name"] for r in res_neg_int}, {self.rule3_name})

		# Currency field float and numeric string on QB Matrix Temporal
		temp_filters = [["code", "in", self.temp_codes]]
		res_curr = frappe.qb.get_query(
			self.temporal_doctype, filters=[*temp_filters, ["currency_field", "=", 99.99]]
		).run(as_dict=True)
		self.assertEqual({r["name"] for r in res_curr}, {self.temp1_name})

		res_curr_str = frappe.qb.get_query(
			self.temporal_doctype, filters=[*temp_filters, ["currency_field", "=", "50.00"]]
		).run(as_dict=True)
		self.assertEqual({r["name"] for r in res_curr_str}, {self.temp3_name})

	def test_03_date_and_datetime_iso_and_python_objects(self):
		"""ISO date/datetime strings and Python date/datetime objects."""
		temp_filters = [["code", "in", self.temp_codes]]

		# ISO Date string
		res_date_str = frappe.qb.get_query(
			self.temporal_doctype, filters=[*temp_filters, ["date_field", "=", "2026-03-01"]]
		).run(as_dict=True)
		self.assertEqual({r["name"] for r in res_date_str}, {self.temp1_name})

		# Python datetime.date
		d_obj = datetime.date(2026, 3, 1)
		res_date_obj = frappe.qb.get_query(
			self.temporal_doctype, filters=[*temp_filters, ["date_field", "=", d_obj]]
		).run(as_dict=True)
		self.assertEqual({r["name"] for r in res_date_obj}, {self.temp1_name})

		# Datetime string and boundary inclusivity on Data Review Task
		task_filters = [["name", "in", [self.task1_name, self.task2_name, self.task3_name]]]
		res_dt_str = frappe.qb.get_query(
			"Data Review Task", filters=[*task_filters, ["resolved_on", ">=", "2026-03-15 00:00:00"]]
		).run(as_dict=True)
		self.assertEqual({r["name"] for r in res_dt_str}, {self.task2_name, self.task3_name})

		# Datetime between range with microsecond boundary
		res_dt_between = frappe.qb.get_query(
			"Data Review Task",
			filters=[
				*task_filters,
				["resolved_on", "between", ["2026-03-01 00:00:00", "2026-03-31 23:59:59.999999"]],
			],
		).run(as_dict=True)
		self.assertEqual(
			{r["name"] for r in res_dt_between}, {self.task1_name, self.task2_name, self.task3_name}
		)

		# Python datetime.datetime object
		dt_obj = datetime.datetime(2026, 3, 15, 18, 30, 0)
		res_dt_obj = frappe.qb.get_query(
			"Data Review Task", filters=[*task_filters, ["resolved_on", "=", dt_obj]]
		).run(as_dict=True)
		self.assertEqual({r["name"] for r in res_dt_obj}, {self.task2_name})
