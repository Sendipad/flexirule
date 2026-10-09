# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

from typing import ClassVar

import frappe
from frappe.tests.utils import FrappeTestCase


class TestQBFieldPathCapabilities(FrappeTestCase):
	"""
	Empirical Test Suite: Field Path Capabilities and Relationship Depth Limits
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
		frappe.db.delete("QB Path Child")
		frappe.db.delete("QB Path Parent")
		frappe.db.delete("QB Path Target 1")
		frappe.db.delete("QB Path Target 2")

		for dt in cls._created_doctypes:
			if frappe.db.exists("DocType", dt):
				frappe.delete_doc(dt, force=True, ignore_permissions=True)

		frappe.db.commit()
		super().tearDownClass()

	@classmethod
	def _setup_test_doctypes(cls):
		# Target 2 (Level 2)
		dt2 = "QB Path Target 2"
		if not frappe.db.exists("DocType", dt2):
			frappe.get_doc(
				{
					"doctype": "DocType",
					"name": dt2,
					"module": "RuleFlow",
					"custom": 1,
					"fields": [
						{
							"fieldname": "target2_name",
							"fieldtype": "Data",
							"label": "Target 2 Name",
							"reqd": 1,
						},
						{"fieldname": "code", "fieldtype": "Data", "label": "Code"},
					],
				}
			).insert(ignore_permissions=True)
			cls._created_doctypes.append(dt2)

		# Target 1 (Level 1)
		dt1 = "QB Path Target 1"
		if not frappe.db.exists("DocType", dt1):
			frappe.get_doc(
				{
					"doctype": "DocType",
					"name": dt1,
					"module": "RuleFlow",
					"custom": 1,
					"fields": [
						{
							"fieldname": "target1_name",
							"fieldtype": "Data",
							"label": "Target 1 Name",
							"reqd": 1,
						},
						{
							"fieldname": "target2_link",
							"fieldtype": "Link",
							"options": dt2,
							"label": "Target 2 Link",
						},
						{"fieldname": "region", "fieldtype": "Data", "label": "Region"},
					],
				}
			).insert(ignore_permissions=True)
			cls._created_doctypes.append(dt1)

		# Child Table
		dt_child = "QB Path Child"
		if not frappe.db.exists("DocType", dt_child):
			frappe.get_doc(
				{
					"doctype": "DocType",
					"name": dt_child,
					"module": "RuleFlow",
					"custom": 1,
					"istable": 1,
					"fields": [
						{"fieldname": "item_code", "fieldtype": "Data", "label": "Item Code"},
						{"fieldname": "qty", "fieldtype": "Float", "label": "Qty"},
						{
							"fieldname": "target1_link",
							"fieldtype": "Link",
							"options": dt1,
							"label": "Target 1 Link",
						},
					],
				}
			).insert(ignore_permissions=True)
			cls._created_doctypes.append(dt_child)

		# Parent Table
		dt_parent = "QB Path Parent"
		if not frappe.db.exists("DocType", dt_parent):
			frappe.get_doc(
				{
					"doctype": "DocType",
					"name": dt_parent,
					"module": "RuleFlow",
					"custom": 1,
					"fields": [
						{"fieldname": "title", "fieldtype": "Data", "label": "Title"},
						{
							"fieldname": "target1_link",
							"fieldtype": "Link",
							"options": dt1,
							"label": "Target 1 Link",
						},
						{"fieldname": "items", "fieldtype": "Table", "options": dt_child, "label": "Items"},
					],
				}
			).insert(ignore_permissions=True)
			cls._created_doctypes.append(dt_parent)

		frappe.db.commit()

	@classmethod
	def _setup_test_records(cls):
		frappe.db.delete("QB Path Child")
		frappe.db.delete("QB Path Parent")
		frappe.db.delete("QB Path Target 1")
		frappe.db.delete("QB Path Target 2")

		cls.t2 = frappe.get_doc(
			{
				"doctype": "QB Path Target 2",
				"target2_name": "T2",
				"code": "C2",
			}
		).insert(ignore_permissions=True)

		cls.t1 = frappe.get_doc(
			{
				"doctype": "QB Path Target 1",
				"target1_name": "T1",
				"target2_link": cls.t2.name,
				"region": "North",
			}
		).insert(ignore_permissions=True)

		cls.p1 = frappe.get_doc(
			{
				"doctype": "QB Path Parent",
				"title": "P1",
				"target1_link": cls.t1.name,
				"items": [
					{"item_code": "I1", "qty": 10.0, "target1_link": cls.t1.name},
				],
			}
		).insert(ignore_permissions=True)

		frappe.db.commit()

	def test_01_one_level_link_path_selection_and_filtering(self):
		"""1-level Link path ('target1_link.region') is supported in both select and filters."""
		q = frappe.qb.get_query(
			"QB Path Parent",
			fields=["name", "target1_link.region"],
			filters={"target1_link.region": "North"},
		)
		sql = q.get_sql()
		self.assertIn("LEFT JOIN `tabQB Path Target 1`", sql)

		res = q.run(as_dict=True)
		self.assertEqual(len(res), 1)
		self.assertEqual(res[0]["name"], self.p1.name)
		self.assertEqual(res[0]["region"], "North")

	def test_02_multi_level_link_path_failure_stage(self):
		"""Multi-level link path ('target1_link.target2_link.code') fails during DynamicTableField.parse stage."""
		# DynamicTableField.parse does linked_fieldname, fieldname = field.split(".")
		# With >1 dot, field.split(".") produces 3+ parts, raising ValueError ("too many values to unpack").
		with self.assertRaises(ValueError) as ctx:
			frappe.qb.get_query(
				"QB Path Parent",
				fields=["name", "target1_link.target2_link.code"],
			)
		self.assertIn("too many values to unpack", str(ctx.exception))

	def test_03_child_table_field_selection_and_filtering(self):
		"""Direct child table field path ('items.item_code') is supported natively."""
		q = frappe.qb.get_query(
			"QB Path Parent",
			fields=["name", "items.item_code"],
			filters={"items.item_code": "I1"},
		)
		sql = q.get_sql()
		self.assertIn("LEFT JOIN `tabQB Path Child`", sql)

		res = q.run(as_dict=True)
		self.assertEqual(len(res), 1)
		self.assertEqual(res[0]["name"], self.p1.name)
		self.assertEqual(res[0]["item_code"], "I1")

	def test_04_child_table_link_field_path_failure_stage(self):
		"""Link field inside child table path ('items.target1_link.region') fails during parse."""
		with self.assertRaises(ValueError) as ctx:
			frappe.qb.get_query(
				"QB Path Parent",
				fields=["name", "items.target1_link.region"],
			)
		self.assertIn("too many values to unpack", str(ctx.exception))

	def test_05_direct_child_query_parent_field(self):
		"""Querying child table directly allows selecting 'parent' column as data string."""
		q = frappe.qb.get_query("QB Path Child", fields=["name", "item_code", "parent"])
		res = q.run(as_dict=True)
		self.assertEqual(len(res), 1)
		self.assertEqual(res[0]["parent"], self.p1.name)
