# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

import unittest

import frappe
from frappe.tests.utils import FrappeTestCase
from pypika import Field


class TestFrappeQBCapabilities(FrappeTestCase):
	"""
	Comprehensive Backend Capability Audit for frappe.qb.get_query in Frappe v15.

	Tests all documented and undocumented capabilities of frappe.qb.get_query against
	the actual installed Frappe v15 / MariaDB environment.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls._setup_test_doctypes()
		cls._setup_test_records()

	@classmethod
	def _setup_test_doctypes(cls):
		# 1. Target DocType for Link relationships
		if not frappe.db.exists("DocType", "QB Test Target"):
			frappe.get_doc(
				{
					"doctype": "DocType",
					"name": "QB Test Target",
					"module": "RuleFlow",
					"custom": 1,
					"fields": [
						{"fieldname": "target_name", "fieldtype": "Data", "label": "Target Name", "reqd": 1},
						{"fieldname": "territory", "fieldtype": "Data", "label": "Territory"},
					],
				}
			).insert(ignore_permissions=True)

		# 2. Child Table DocType
		if not frappe.db.exists("DocType", "QB Test Child"):
			frappe.get_doc(
				{
					"doctype": "DocType",
					"name": "QB Test Child",
					"module": "RuleFlow",
					"custom": 1,
					"istable": 1,
					"fields": [
						{"fieldname": "item_code", "fieldtype": "Data", "label": "Item Code"},
						{"fieldname": "qty", "fieldtype": "Float", "label": "Qty"},
						{"fieldname": "rate", "fieldtype": "Currency", "label": "Rate"},
						{"fieldname": "amount", "fieldtype": "Currency", "label": "Amount"},
					],
				}
			).insert(ignore_permissions=True)

		# 3. Parent DocType
		if not frappe.db.exists("DocType", "QB Test Parent"):
			frappe.get_doc(
				{
					"doctype": "DocType",
					"name": "QB Test Parent",
					"module": "RuleFlow",
					"custom": 1,
					"fields": [
						{"fieldname": "parent_title", "fieldtype": "Data", "label": "Title"},
						{"fieldname": "status", "fieldtype": "Data", "label": "Status"},
						{"fieldname": "enabled", "fieldtype": "Check", "label": "Enabled"},
						{
							"fieldname": "target_link",
							"fieldtype": "Link",
							"options": "QB Test Target",
							"label": "Target Link",
						},
						{
							"fieldname": "items",
							"fieldtype": "Table",
							"options": "QB Test Child",
							"label": "Items",
						},
					],
				}
			).insert(ignore_permissions=True)

		frappe.db.commit()

	@classmethod
	def _setup_test_records(cls):
		frappe.db.delete("QB Test Parent")
		frappe.db.delete("QB Test Target")

		cls.target1 = frappe.get_doc(
			{"doctype": "QB Test Target", "target_name": "T1", "territory": "North"}
		).insert(ignore_permissions=True)
		cls.target2 = frappe.get_doc(
			{"doctype": "QB Test Target", "target_name": "T2", "territory": "South"}
		).insert(ignore_permissions=True)

		cls.p1 = frappe.get_doc(
			{
				"doctype": "QB Test Parent",
				"parent_title": "P1",
				"status": "Open",
				"enabled": 1,
				"target_link": cls.target1.name,
				"items": [
					{"item_code": "ITEM-001", "qty": 2, "rate": 10, "amount": 20},
					{"item_code": "ITEM-002", "qty": 5, "rate": 20, "amount": 100},
				],
			}
		).insert(ignore_permissions=True)

		cls.p2 = frappe.get_doc(
			{
				"doctype": "QB Test Parent",
				"parent_title": "P2",
				"status": "Pending",
				"enabled": 1,
				"target_link": cls.target2.name,
				"items": [{"item_code": "ITEM-001", "qty": 1, "rate": 10, "amount": 10}],
			}
		).insert(ignore_permissions=True)

		cls.p3 = frappe.get_doc(
			{"doctype": "QB Test Parent", "parent_title": "P3", "status": "Closed", "enabled": 0, "items": []}
		).insert(ignore_permissions=True)

		frappe.db.commit()

	# -------------------------------------------------------------------------
	# 1. Basic get_query() Behavior & Fields
	# -------------------------------------------------------------------------
	def test_01_basic_get_query_and_fields(self):
		# Basic query with default fields
		q = frappe.qb.get_query("QB Test Parent")
		sql = q.get_sql()
		self.assertIn("SELECT", sql)
		self.assertIn("`tabQB Test Parent`", sql)

		# Explicit list of fields
		q_fields = frappe.qb.get_query("QB Test Parent", fields=["name", "status"])
		res_dict = q_fields.run(as_dict=True)
		self.assertIsInstance(res_dict, list)
		self.assertTrue(len(res_dict) >= 3)
		self.assertIn("name", res_dict[0])
		self.assertIn("status", res_dict[0])

		# Comma-separated string fields
		q_str = frappe.qb.get_query("QB Test Parent", fields="name, status")
		res_str = q_str.run(as_dict=True)
		self.assertEqual(len(res_str), len(res_dict))

		# Asterisk fields="*"
		q_star = frappe.qb.get_query("QB Test Parent", fields="*")
		res_star = q_star.run(as_dict=True)
		self.assertIn("parent_title", res_star[0])
		self.assertIn("creation", res_star[0])

		# Field Aliases
		q_alias = frappe.qb.get_query("QB Test Parent", fields=["name as doc_id", "status as state"])
		res_alias = q_alias.run(as_dict=True)
		self.assertIn("doc_id", res_alias[0])
		self.assertIn("state", res_alias[0])

	def test_02_execution_modes(self):
		q = frappe.qb.get_query("QB Test Parent", fields=["name", "status"], limit=2)

		# 1. default / tuple list
		res_default = q.run()
		self.assertIsInstance(res_default, (tuple, list))
		self.assertEqual(len(res_default), 2)
		self.assertIsInstance(res_default[0], (tuple, list))

		# 2. as_dict=True
		res_dict = q.run(as_dict=True)
		self.assertIsInstance(res_dict, list)
		self.assertIsInstance(res_dict[0], dict)

		# 3. as_list=True
		res_list = q.run(as_list=True)
		self.assertIsInstance(res_list, (tuple, list))
		self.assertIsInstance(res_list[0], (tuple, list))

		# 4. pluck=True
		q_pluck = frappe.qb.get_query("QB Test Parent", fields=["name"], limit=2)
		res_pluck = q_pluck.run(pluck=True)
		self.assertIsInstance(res_pluck, (tuple, list))
		self.assertIsInstance(res_pluck[0], str)

	# -------------------------------------------------------------------------
	# 2. Filter Syntax & Logic
	# -------------------------------------------------------------------------
	def test_03_filter_forms_and_logic(self):
		# Dict equality
		q1 = frappe.qb.get_query("QB Test Parent", filters={"status": "Open"})
		res1 = q1.run(as_dict=True)
		self.assertEqual(len(res1), 1)
		self.assertEqual(res1[0]["name"], self.p1.name)

		# Dict operator form
		q2 = frappe.qb.get_query("QB Test Parent", filters={"enabled": [">", 0]})
		res2 = q2.run(as_dict=True)
		self.assertEqual(len(res2), 2)

		# List form
		q3 = frappe.qb.get_query("QB Test Parent", filters=[["status", "=", "Open"]])
		res3 = q3.run(as_dict=True)
		self.assertEqual(len(res3), 1)

		# Documented string "or" in filters list is NOT supported (parsed as name="or" filter)
		q_or = frappe.qb.get_query(
			"QB Test Parent", filters=[["status", "=", "Open"], "or", ["status", "=", "Pending"]]
		)
		res_or = q_or.run(as_dict=True)
		# String "or" gets converted to filter name='or', yielding 0 records
		self.assertEqual(len(res_or), 0)

		# Working OR logic via Pypika Criterion
		t = frappe.qb.DocType("QB Test Parent")
		q_pypika_or = frappe.qb.get_query(
			"QB Test Parent", filters=(t.status == "Open") | (t.status == "Pending")
		)
		res_pypika_or = q_pypika_or.run(as_dict=True)
		self.assertEqual(len(res_pypika_or), 2)

	def test_04_filter_operators(self):
		ops_to_test = [
			("=", "Open", 1),
			("!=", "Open", 2),
			(">", 0, 2),
			("<", 1, 1),
			(">=", 1, 2),
			("<=", 0, 1),
			("like", "%pe%", 2),  # "Open" and "Pending" both contain "pe"
			("not like", "%pe%", 1),  # "Closed" does not contain "pe"
			("in", ["Open", "Pending"], 2),
			("not in", ["Open", "Pending"], 1),
			("is", "set", 3),
			("is", "not set", 0),
		]

		for op, val, expected_count in ops_to_test:
			with self.subTest(op=op, val=val):
				q = frappe.qb.get_query(
					"QB Test Parent",
					filters=[["status" if op not in (">", "<", ">=", "<=") else "enabled", op, val]],
				)
				res = q.run(as_dict=True)
				self.assertEqual(
					len(res),
					expected_count,
					f"Failed for op '{op}' with val '{val}'. Got {len(res)}, expected {expected_count}",
				)

		# Tree / Nested set operators: "descendants of" / "ancestors of"
		# Test that invalid operator raises KeyError / Exception in Engine operator mapping
		with self.assertRaises(Exception):
			q_desc = frappe.qb.get_query("QB Test Parent", filters=[["status", "descendants of", "Open"]])
			q_desc.run(as_dict=True)

	# -------------------------------------------------------------------------
	# 3. Link-Field Traversal
	# -------------------------------------------------------------------------
	def test_05_link_field_traversal(self):
		# Selection (Generates LEFT JOIN tabQB Test Target)
		q = frappe.qb.get_query("QB Test Parent", fields=["name", "target_link.territory"])
		sql = q.get_sql()
		self.assertIn("LEFT JOIN `tabQB Test Target`", sql)
		res = q.run(as_dict=True)
		self.assertTrue(any(r.get("territory") == "North" for r in res))

		# Filtering
		q_filter = frappe.qb.get_query("QB Test Parent", filters={"target_link.territory": "North"})
		res_filter = q_filter.run(as_dict=True)
		self.assertEqual(len(res_filter), 1)
		self.assertEqual(res_filter[0]["name"], self.p1.name)

		# Alias on linked field
		q_alias = frappe.qb.get_query("QB Test Parent", fields=["target_link.territory as dest_region"])
		res_alias = q_alias.run(as_dict=True)
		self.assertIn("dest_region", res_alias[0])

		# Order by dotted linked field is UNSUPPORTED in order_by string (raises OperationalError: Unknown column)
		with self.assertRaises(Exception):
			q_order = frappe.qb.get_query(
				"QB Test Parent",
				fields=["name", "target_link.territory"],
				order_by="target_link.territory asc",
			)
			q_order.run(as_dict=True)

	# -------------------------------------------------------------------------
	# 4. Child Table Traversal & Structured Child Fetching
	# -------------------------------------------------------------------------
	def test_06_child_table_traversal(self):
		# Dotted child field selection
		q = frappe.qb.get_query("QB Test Parent", fields=["name", "items.item_code"])
		sql = q.get_sql()
		self.assertIn("LEFT JOIN `tabQB Test Child`", sql)
		res = q.run(as_dict=True)
		# Parent P1 has 2 items -> duplicated parent row in result set
		p1_rows = [r for r in res if r["name"] == self.p1.name]
		self.assertEqual(len(p1_rows), 2)

		# Distinct with child join
		q_dist = frappe.qb.get_query(
			"QB Test Parent", fields=["name"], filters={"items.item_code": "ITEM-001"}, distinct=True
		)
		res_dist = q_dist.run(as_dict=True)
		self.assertEqual(len(res_dist), 2)  # P1 and P2 both have ITEM-001

		# Filtering child fields
		q_child_filter = frappe.qb.get_query("QB Test Parent", filters={"items.item_code": "ITEM-002"})
		res_child_filter = q_child_filter.run(as_dict=True)
		self.assertEqual(len(res_child_filter), 1)
		self.assertEqual(res_child_filter[0]["name"], self.p1.name)

		# Structured dict child fetching: fields=["name", {"items": ["item_code", "qty"]}]
		q_struct = frappe.qb.get_query("QB Test Parent", fields=["name", {"items": ["item_code", "qty"]}])
		res_struct = q_struct.run(as_dict=True)
		self.assertIsInstance(res_struct, list)
		p1_struct = next(r for r in res_struct if r["name"] == self.p1.name)
		self.assertIn("items", p1_struct)
		self.assertIsInstance(p1_struct["items"], list)
		self.assertEqual(len(p1_struct["items"]), 2)
		self.assertEqual(p1_struct["items"][0]["item_code"], "ITEM-001")

	# -------------------------------------------------------------------------
	# 5. Default Fields: fields="*" vs fields=None
	# -------------------------------------------------------------------------
	def test_07_default_fields_behavior(self):
		# Omitted fields -> defaults to name field
		q_none = frappe.qb.get_query("QB Test Parent")
		res_none = q_none.run(as_dict=True)

		q_star = frappe.qb.get_query("QB Test Parent", fields="*")
		res_star = q_star.run(as_dict=True)

		self.assertIn("name", res_none[0])
		self.assertIn("parent_title", res_star[0])

	# -------------------------------------------------------------------------
	# 6. Aggregation Functions
	# -------------------------------------------------------------------------
	def test_08_aggregation_functions(self):
		# Documented dict syntax fields=[{"COUNT": "name"}] is UNSUPPORTED (raises AttributeError: 'NoneType' object has no attribute 'fieldtype')
		with self.assertRaises(AttributeError):
			frappe.qb.get_query("QB Test Parent", fields=[{"COUNT": "name", "as": "total_count"}])

		# WORKING syntax 1: SQL string function expressions
		q_count_str = frappe.qb.get_query("QB Test Parent", fields=["count(name) as total_count"])
		res_count_str = q_count_str.run(as_dict=True)
		self.assertIn("total_count", res_count_str[0])
		self.assertEqual(res_count_str[0]["total_count"], 3)

		q_count_star = frappe.qb.get_query("QB Test Parent", fields=["count(*) as total_star"])
		res_count_star = q_count_star.run(as_dict=True)
		self.assertEqual(res_count_star[0]["total_star"], 3)

		q_sum_str = frappe.qb.get_query("QB Test Parent", fields=["sum(enabled) as sum_enabled"])
		res_sum_str = q_sum_str.run(as_dict=True)
		self.assertEqual(res_sum_str[0]["sum_enabled"], 2)

		# WORKING syntax 2: Pypika functions
		from frappe.query_builder.functions import Count, Sum

		t = frappe.qb.DocType("QB Test Parent")
		q_pypika_agg = frappe.qb.get_query(
			"QB Test Parent", fields=[Count(t.name).as_("total"), Sum(t.enabled).as_("enabled_sum")]
		)
		res_pypika_agg = q_pypika_agg.run(as_dict=True)
		self.assertEqual(res_pypika_agg[0]["total"], 3)
		self.assertEqual(res_pypika_agg[0]["enabled_sum"], 2)

	# -------------------------------------------------------------------------
	# 7. Scalar Functions
	# -------------------------------------------------------------------------
	def test_09_scalar_functions(self):
		# Documented dict syntax fields=[{"IFNULL": ...}] is UNSUPPORTED (raises AttributeError)
		with self.assertRaises(AttributeError):
			frappe.qb.get_query(
				"QB Test Parent", fields=["name", {"IFNULL": ["target_link", "'None'"], "as": "safe_link"}]
			)

		# String function "now() as current_time" is UNSUPPORTED (raises OperationalError: Unknown column 'now()')
		with self.assertRaises(Exception):
			q_now_str = frappe.qb.get_query("QB Test Parent", fields=["now() as current_time"], limit=1)
			q_now_str.run(as_dict=True)

		# WORKING syntax: Frappe QB / Pypika Now() function
		from frappe.query_builder.functions import Now

		q_now = frappe.qb.get_query("QB Test Parent", fields=[Now().as_("current_time")], limit=1)
		res_now = q_now.run(as_dict=True)
		self.assertIn("current_time", res_now[0])

	# -------------------------------------------------------------------------
	# 8. Order By, Group By, Pagination, Distinct
	# -------------------------------------------------------------------------
	def test_10_order_by_group_by_pagination_distinct(self):
		# Order by multiple fields
		q_order = frappe.qb.get_query(
			"QB Test Parent", fields=["name", "status"], order_by="status asc, name desc"
		)
		res_order = q_order.run(as_dict=True)
		self.assertEqual(len(res_order), 3)

		# Group by
		q_group = frappe.qb.get_query("QB Test Parent", fields=["enabled"], group_by="enabled")
		res_group = q_group.run(as_dict=True)
		self.assertEqual(len(res_group), 2)

		# Pagination limit & offset
		q_page = frappe.qb.get_query(
			"QB Test Parent", fields=["name"], order_by="name asc", limit=1, offset=1
		)
		res_page = q_page.run(as_dict=True)
		self.assertEqual(len(res_page), 1)

		# Distinct
		q_dist = frappe.qb.get_query("QB Test Parent", fields=["enabled"], distinct=True)
		res_dist = q_dist.run(as_dict=True)
		self.assertEqual(len(res_dist), 2)

	# -------------------------------------------------------------------------
	# 9. Permissions & Context
	# -------------------------------------------------------------------------
	def test_11_permissions_and_user_context(self):
		# Engine().get_query does NOT take ignore_permissions kwarg directly (raises TypeError)
		with self.assertRaises(TypeError):
			frappe.qb.get_query("QB Test Parent", ignore_permissions=True)

		# Engine().get_query does NOT take user kwarg directly (raises TypeError)
		with self.assertRaises(TypeError):
			frappe.qb.get_query("QB Test Parent", user="Administrator")

		# Permission checks are performed via frappe.database.query.Permission.check_permissions
		from frappe.database.query import Permission

		q = frappe.qb.get_query("QB Test Parent", fields=["name"])
		# Permission.check_permissions verifies user permissions against the generated query SQL
		Permission.check_permissions(q, user="Administrator")

	# -------------------------------------------------------------------------
	# 10. Debug & SQL Inspection
	# -------------------------------------------------------------------------
	def test_12_debug_and_sql_inspection(self):
		q = frappe.qb.get_query("QB Test Parent", fields=["name", "status"])
		sql = q.get_sql()
		self.assertIsInstance(sql, str)
		self.assertIn("SELECT `name`,`status` FROM `tabQB Test Parent`", sql)

		# query.run(debug=True) prints SQL to console
		try:
			q.run(debug=True, as_dict=True)
		except Exception as e:
			self.fail(f"query.run(debug=True) raised error: {e}")

	# -------------------------------------------------------------------------
	# 11. Pypika Objects Integration
	# -------------------------------------------------------------------------
	def test_13_pypika_objects_integration(self):
		# Pypika Field object in fields list
		f_title = Field("parent_title")
		q_pypika_field = frappe.qb.get_query("QB Test Parent", fields=["name", f_title])
		res_field = q_pypika_field.run(as_dict=True)
		self.assertIn("parent_title", res_field[0])

		# Pypika Criterion object in filters
		p_criterion = Field("enabled") == 1
		q_pypika_crit = frappe.qb.get_query("QB Test Parent", filters=p_criterion)
		res_crit = q_pypika_crit.run(as_dict=True)
		self.assertEqual(len(res_crit), 2)

	# -------------------------------------------------------------------------
	# 12. Record Locking
	# -------------------------------------------------------------------------
	def test_14_record_locking(self):
		# for_update=True
		q_lock = frappe.qb.get_query("QB Test Parent", fields=["name"], limit=1, for_update=True)
		sql_lock = q_lock.get_sql()
		self.assertIn("FOR UPDATE", sql_lock)

	# -------------------------------------------------------------------------
	# 13. Security & Input Validation
	# -------------------------------------------------------------------------
	def test_15_security_and_validation(self):
		# Invalid field name -> raises OperationalError on execution
		with self.assertRaises(Exception):
			q_invalid = frappe.qb.get_query("QB Test Parent", fields=["non_existent_column_12345"])
			q_invalid.run(as_dict=True)

		# Unknown link traversal field -> raises OperationalError / AttributeError
		with self.assertRaises(Exception):
			q_bad_link = frappe.qb.get_query("QB Test Parent", fields=["non_existent_link.territory"])
			q_bad_link.run(as_dict=True)
