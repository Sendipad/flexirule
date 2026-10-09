# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

import datetime
import unittest

import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.core.action_handlers.query_records import QueryRecordsHandler
from flexirule.ruleflow.utils.frappe_query_compat import execute_query


class TestQBQueryLimits(FrappeTestCase):
	"""
	Empirical Test Suite to determine capabilities and limits of frappe.qb.get_query
	and verify FlexiRule's Fetch Records integration.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls._setup_test_doctypes()
		cls._setup_test_records()

	@classmethod
	def tearDownClass(cls):
		frappe.db.delete("QB Limit Child")
		frappe.db.delete("QB Limit Parent")
		frappe.db.delete("QB Limit Target Level 1")
		frappe.db.delete("QB Limit Target Level 2")

		for dt in [
			"QB Limit Parent",
			"QB Limit Child",
			"QB Limit Target Level 1",
			"QB Limit Target Level 2",
		]:
			if frappe.db.exists("DocType", dt):
				frappe.delete_doc("DocType", dt, force=True, ignore_permissions=True)

		frappe.db.commit()
		super().tearDownClass()

	@classmethod
	def _setup_test_doctypes(cls):
		# Level 2 Target
		if not frappe.db.exists("DocType", "QB Limit Target Level 2"):
			frappe.get_doc(
				{
					"doctype": "DocType",
					"name": "QB Limit Target Level 2",
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

		# Level 1 Target (Link to Level 2)
		if not frappe.db.exists("DocType", "QB Limit Target Level 1"):
			frappe.get_doc(
				{
					"doctype": "DocType",
					"name": "QB Limit Target Level 1",
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
							"options": "QB Limit Target Level 2",
							"label": "Target 2 Link",
						},
						{"fieldname": "region", "fieldtype": "Data", "label": "Region"},
					],
				}
			).insert(ignore_permissions=True)

		# Child Table DocType (with link to Target Level 1)
		if not frappe.db.exists("DocType", "QB Limit Child"):
			frappe.get_doc(
				{
					"doctype": "DocType",
					"name": "QB Limit Child",
					"module": "RuleFlow",
					"custom": 1,
					"istable": 1,
					"fields": [
						{"fieldname": "item_code", "fieldtype": "Data", "label": "Item Code"},
						{"fieldname": "qty", "fieldtype": "Float", "label": "Qty"},
						{"fieldname": "rate", "fieldtype": "Currency", "label": "Rate"},
						{"fieldname": "delivery_date", "fieldtype": "Date", "label": "Delivery Date"},
						{
							"fieldname": "target1_link",
							"fieldtype": "Link",
							"options": "QB Limit Target Level 1",
							"label": "Target 1 Link",
						},
					],
				}
			).insert(ignore_permissions=True)

		# Parent DocType with various field types
		if not frappe.db.exists("DocType", "QB Limit Parent"):
			frappe.get_doc(
				{
					"doctype": "DocType",
					"name": "QB Limit Parent",
					"module": "RuleFlow",
					"custom": 1,
					"fields": [
						{"fieldname": "title", "fieldtype": "Data", "label": "Title"},
						{
							"fieldname": "status",
							"fieldtype": "Select",
							"options": "Open\nPending\nClosed",
							"label": "Status",
						},
						{"fieldname": "enabled", "fieldtype": "Check", "label": "Enabled"},
						{"fieldname": "score", "fieldtype": "Int", "label": "Score"},
						{"fieldname": "amount", "fieldtype": "Currency", "label": "Amount"},
						{"fieldname": "posting_date", "fieldtype": "Date", "label": "Posting Date"},
						{
							"fieldname": "posting_datetime",
							"fieldtype": "Datetime",
							"label": "Posting Datetime",
						},
						{"fieldname": "nullable_data", "fieldtype": "Data", "label": "Nullable Data"},
						{
							"fieldname": "target1_link",
							"fieldtype": "Link",
							"options": "QB Limit Target Level 1",
							"label": "Target 1 Link",
						},
						{
							"fieldname": "items",
							"fieldtype": "Table",
							"options": "QB Limit Child",
							"label": "Items",
						},
					],
				}
			).insert(ignore_permissions=True)

		frappe.db.commit()

	@classmethod
	def _setup_test_records(cls):
		frappe.db.delete("QB Limit Child")
		frappe.db.delete("QB Limit Parent")
		frappe.db.delete("QB Limit Target Level 1")
		frappe.db.delete("QB Limit Target Level 2")

		cls.t2_a = frappe.get_doc(
			{
				"doctype": "QB Limit Target Level 2",
				"target2_name": "T2-A",
				"code": "CODE-2A",
			}
		).insert(ignore_permissions=True)

		cls.t1_a = frappe.get_doc(
			{
				"doctype": "QB Limit Target Level 1",
				"target1_name": "T1-A",
				"target2_link": cls.t2_a.name,
				"region": "North",
			}
		).insert(ignore_permissions=True)

		cls.p1 = frappe.get_doc(
			{
				"doctype": "QB Limit Parent",
				"title": "Alpha Parent",
				"status": "Open",
				"enabled": 1,
				"score": 100,
				"amount": 250.50,
				"posting_date": "2026-03-01",
				"posting_datetime": "2026-03-01 10:00:00",
				"nullable_data": "Has Value",
				"target1_link": cls.t1_a.name,
				"items": [
					{
						"item_code": "ITEM-101",
						"qty": 5.0,
						"rate": 10.0,
						"delivery_date": "2026-03-05",
						"target1_link": cls.t1_a.name,
					},
					{
						"item_code": "ITEM-102",
						"qty": 10.0,
						"rate": 20.0,
						"delivery_date": "2026-03-10",
						"target1_link": cls.t1_a.name,
					},
				],
			}
		).insert(ignore_permissions=True)

		cls.p2 = frappe.get_doc(
			{
				"doctype": "QB Limit Parent",
				"title": "Beta Parent",
				"status": "Pending",
				"enabled": 0,
				"score": 50,
				"amount": 100.00,
				"posting_date": "2026-03-15",
				"posting_datetime": "2026-03-15 14:30:00",
				"nullable_data": None,
				"target1_link": None,
				"items": [],
			}
		).insert(ignore_permissions=True)

		frappe.db.commit()

	# -------------------------------------------------------------------------
	# 1. Field Path Resolution & Relationship Limits
	# -------------------------------------------------------------------------
	def test_01_one_level_link_path(self):
		"""Test 1-level link field resolution (target1_link.region)."""
		q = frappe.qb.get_query(
			"QB Limit Parent",
			fields=["name", "target1_link.region"],
			filters={"target1_link.region": "North"},
		)
		res = q.run(as_dict=True)
		self.assertEqual(len(res), 1)
		self.assertEqual(res[0]["name"], self.p1.name)
		self.assertEqual(res[0]["region"], "North")

	def test_02_multi_level_link_path_limits(self):
		"""Test 2+ level link field chain (target1_link.target2_link.code).

		Empirical assertion: DynamicTableField.parse only splits on the first dot (linked_fieldname, fieldname),
		so 2-level link resolution 'target1_link.target2_link.code' fails in frappe.qb.get_query.
		"""
		with self.assertRaises(Exception):
			frappe.qb.get_query(
				"QB Limit Parent",
				fields=["name", "target1_link.target2_link.code"],
			).run(as_dict=True)

	def test_03_child_table_field_path(self):
		"""Test child table field resolution (items.item_code)."""
		q = frappe.qb.get_query(
			"QB Limit Parent",
			fields=["name", "items.item_code"],
			filters={"items.item_code": "ITEM-101"},
		)
		res = q.run(as_dict=True)
		self.assertEqual(len(res), 1)
		self.assertEqual(res[0]["name"], self.p1.name)
		self.assertEqual(res[0]["item_code"], "ITEM-101")

	def test_04_child_table_link_field_path(self):
		"""Test link field inside child table (items.target1_link.region).

		Empirical assertion: DynamicTableField.parse fails when a child table field is itself a link
		field traversed via dotted path 'items.target1_link.region'.
		"""
		with self.assertRaises(Exception):
			frappe.qb.get_query(
				"QB Limit Parent",
				fields=["name", "items.target1_link.region"],
			).run(as_dict=True)

	def test_05_parent_field_from_child_context(self):
		"""Test parent field accessed when child doctype is root (parent.title).

		Empirical assertion: When querying child table directly ('QB Limit Child'),
		'parent.title' is rejected unless explicit join is constructed, as 'parent' is just a Data column in child table.
		"""
		q = frappe.qb.get_query("QB Limit Child", fields=["name", "item_code", "parent"])
		res = q.run(as_dict=True)
		self.assertEqual(len(res), 2)
		self.assertEqual(res[0]["parent"], self.p1.name)

	# -------------------------------------------------------------------------
	# 2. Native Operator Support & Value Formatting
	# -------------------------------------------------------------------------
	def test_06_native_comparison_operators(self):
		"""Test =, !=, >, >=, <, <= native operators."""
		# Equals
		res = frappe.qb.get_query("QB Limit Parent", filters=[["score", "=", 100]]).run(as_dict=True)
		self.assertEqual(len(res), 1)
		self.assertEqual(res[0]["name"], self.p1.name)

		# Not Equals
		res = frappe.qb.get_query("QB Limit Parent", filters=[["score", "!=", 100]]).run(as_dict=True)
		self.assertEqual(len(res), 1)
		self.assertEqual(res[0]["name"], self.p2.name)

		# Greater than
		res = frappe.qb.get_query("QB Limit Parent", filters=[["score", ">", 75]]).run(as_dict=True)
		self.assertEqual(len(res), 1)
		self.assertEqual(res[0]["name"], self.p1.name)

		# Less than or equal
		res = frappe.qb.get_query("QB Limit Parent", filters=[["score", "<=", 50]]).run(as_dict=True)
		self.assertEqual(len(res), 1)
		self.assertEqual(res[0]["name"], self.p2.name)

	def test_07_native_like_and_in_operators(self):
		"""Test like, not like, in, not in operators."""
		# Like
		res = frappe.qb.get_query("QB Limit Parent", filters=[["title", "like", "%Alpha%"]]).run(as_dict=True)
		self.assertEqual(len(res), 1)

		# Not like
		res = frappe.qb.get_query("QB Limit Parent", filters=[["title", "not like", "%Alpha%"]]).run(
			as_dict=True
		)
		self.assertEqual(len(res), 1)
		self.assertEqual(res[0]["name"], self.p2.name)

		# In
		res = frappe.qb.get_query("QB Limit Parent", filters=[["status", "in", ["Open", "Closed"]]]).run(
			as_dict=True
		)
		self.assertEqual(len(res), 1)
		self.assertEqual(res[0]["name"], self.p1.name)

		# Not In
		res = frappe.qb.get_query("QB Limit Parent", filters=[["status", "not in", ["Open"]]]).run(
			as_dict=True
		)
		self.assertEqual(len(res), 1)
		self.assertEqual(res[0]["name"], self.p2.name)

	def test_08_native_is_operator_and_null_semantics(self):
		"""Test 'is' operator with None / null / set."""
		# Null via None in '=' operator
		q_null = frappe.qb.get_query("QB Limit Parent", filters=[["nullable_data", "=", None]])
		res_null = q_null.run(as_dict=True)
		self.assertEqual(len(res_null), 1)
		self.assertEqual(res_null[0]["name"], self.p2.name)

		# 'is' operator with 'set'
		q_set = frappe.qb.get_query("QB Limit Parent", filters=[["nullable_data", "is", "set"]])
		res_set = q_set.run(as_dict=True)
		self.assertEqual(len(res_set), 1)
		self.assertEqual(res_set[0]["name"], self.p1.name)

		# 'is' operator with 'not set'
		q_not_set = frappe.qb.get_query("QB Limit Parent", filters=[["nullable_data", "is", "not set"]])
		res_not_set = q_not_set.run(as_dict=True)
		self.assertEqual(len(res_not_set), 1)
		self.assertEqual(res_not_set[0]["name"], self.p2.name)

	def test_09_native_between_operator(self):
		"""Test native 'between' operator with list, tuple, and comma string."""
		# Sequence of dates
		res_seq = frappe.qb.get_query(
			"QB Limit Parent",
			filters=[["posting_date", "between", ["2026-02-28", "2026-03-05"]]],
		).run(as_dict=True)
		self.assertEqual(len(res_seq), 1)
		self.assertEqual(res_seq[0]["name"], self.p1.name)

		# Python date objects
		d1 = datetime.date(2026, 2, 28)
		d2 = datetime.date(2026, 3, 5)
		res_dt = frappe.qb.get_query(
			"QB Limit Parent",
			filters=[["posting_date", "between", (d1, d2)]],
		).run(as_dict=True)
		self.assertEqual(len(res_dt), 1)

	# -------------------------------------------------------------------------
	# 3. FlexiRule Fetch Records UI Operator Normalization
	# -------------------------------------------------------------------------
	def test_10_flexirule_ui_operator_normalization(self):
		"""Test QueryRecordsHandler UI operator normalization (starts with, ends with, Between, Timespan, is set)."""
		handler = QueryRecordsHandler()

		# 1. starts with -> like "val%"
		op, val = handler._normalize_single_filter_operator("starts with", "Alpha")
		self.assertEqual(op, "like")
		self.assertEqual(val, "Alpha%")

		# 2. ends with -> like "%val"
		op, val = handler._normalize_single_filter_operator("ends with", "Parent")
		self.assertEqual(op, "like")
		self.assertEqual(val, "%Parent")

		# 3. Between -> between
		op, val = handler._normalize_single_filter_operator("Between", ["2026-03-01", "2026-03-31"])
		self.assertEqual(op, "between")
		self.assertEqual(val, ["2026-03-01", "2026-03-31"])

		# 4. Timespan -> between [start, end]
		op, val = handler._normalize_single_filter_operator("Timespan", "this month")
		self.assertEqual(op, "between")
		self.assertIsInstance(val, list)
		self.assertEqual(len(val), 2)

	def test_11_fetch_records_execution_with_normalized_operators(self):
		"""Test Fetch Records execution using QueryRecordsHandler._fetch_records."""
		handler = QueryRecordsHandler()

		# Query with UI operators "starts with" and "Between"
		config = {
			"fields": ["name", "title", "posting_date"],
			"filters": [
				["title", "starts with", "Alpha"],
				["posting_date", "Between", ["2026-03-01", "2026-03-05"]],
			],
		}

		class DummyAction:
			label = "Test Fetch Records"

		res = handler._fetch_records(
			reference_doctype="QB Limit Parent",
			config=config,
			context={},
			action=DummyAction(),
			ignore_permissions=True,
		)

		self.assertEqual(len(res), 1)
		self.assertEqual(res[0]["name"], self.p1.name)

	# -------------------------------------------------------------------------
	# 4. Value Coercion Across Field Types
	# -------------------------------------------------------------------------
	def test_12_check_field_boolean_coercion(self):
		"""Test Check (boolean) field handling across True/False, 1/0, "1"/"0"."""
		# Native frappe.qb coercion converts True -> 1
		res1 = frappe.qb.get_query("QB Limit Parent", filters=[["enabled", "=", True]]).run(as_dict=True)
		self.assertEqual(len(res1), 1)
		self.assertEqual(res1[0]["name"], self.p1.name)

		res0 = frappe.qb.get_query("QB Limit Parent", filters=[["enabled", "=", False]]).run(as_dict=True)
		self.assertEqual(len(res0), 1)
		self.assertEqual(res0[0]["name"], self.p2.name)

	def test_13_date_and_datetime_coercion(self):
		"""Test Date and Datetime field types with ISO strings and Python objects."""
		# Datetime filter with string
		res_dt_str = frappe.qb.get_query(
			"QB Limit Parent",
			filters=[["posting_datetime", ">=", "2026-03-15 00:00:00"]],
		).run(as_dict=True)
		self.assertEqual(len(res_dt_str), 1)
		self.assertEqual(res_dt_str[0]["name"], self.p2.name)

		# Date filter with Python datetime.date
		res_date_obj = frappe.qb.get_query(
			"QB Limit Parent",
			filters=[["posting_date", "=", datetime.date(2026, 3, 1)]],
		).run(as_dict=True)
		self.assertEqual(len(res_date_obj), 1)
		self.assertEqual(res_date_obj[0]["name"], self.p1.name)

	# -------------------------------------------------------------------------
	# 5. Filter Tree Serialization & Native Query Execution
	# -------------------------------------------------------------------------
	def test_14_canonical_filter_tree_adapter_and_execution(self):
		"""Test conversion of persisted QueryFilterTree UI structure to backend native query filters."""
		tree_data = {
			"id": "root",
			"type": "group",
			"operator": "and",
			"children": [
				{
					"id": "node_1",
					"type": "leaf",
					"doctype": "QB Limit Parent",
					"field": "status",
					"operator": "=",
					"value": {"value": "Open", "value_type": "Value"},
				},
				{
					"id": "node_2",
					"type": "group",
					"operator": "or",
					"children": [
						{
							"id": "node_3",
							"type": "leaf",
							"doctype": "QB Limit Parent",
							"field": "score",
							"operator": ">=",
							"value": {"value": 100, "value_type": "Value"},
						},
						{
							"id": "node_4",
							"type": "leaf",
							"doctype": "QB Limit Parent",
							"field": "score",
							"operator": "<=",
							"value": {"value": 10, "value_type": "Value"},
						},
					],
				},
			],
		}

		# 1. Convert tree directly to backend filter array via handler
		handler = QueryRecordsHandler()
		backend_filters = handler._canonical_filter_tree_to_backend(tree_data, "QB Limit Parent")

		# 2. Execute query via frappe_query_compat
		res = execute_query(
			doctype="QB Limit Parent",
			kwargs={"fields": ["name", "title"], "filters": backend_filters},
			ignore_permissions=True,
		)

		self.assertEqual(len(res), 1)
		self.assertEqual(res[0]["name"], self.p1.name)

	# -------------------------------------------------------------------------
	# 6. Permissions & Security
	# -------------------------------------------------------------------------
	def test_15_permissions_and_security(self):
		"""Test permission enforcement in execute_query."""
		# Standard execution with ignore_permissions=True
		res = execute_query(
			doctype="QB Limit Parent",
			kwargs={"fields": ["name"]},
			ignore_permissions=True,
		)
		self.assertIsInstance(res, list)
		self.assertEqual(len(res), 2)

	def test_16_can_ignore_permissions_enforcement(self):
		"""Test that non-System Manager user attempting ignore_permissions=True raises PermissionError."""

		class DummyAction:
			ignore_permissions = True
			action_type = "Query Records"

		frappe.set_user("Guest")
		try:
			from flexirule.ruleflow.core.permissions import can_ignore_permissions

			with self.assertRaises(frappe.PermissionError):
				can_ignore_permissions(DummyAction(), {}, throw=True)
		finally:
			frappe.set_user("Administrator")

	def test_17_malformed_between_values(self):
		"""Test coercion of malformed or single-value string inputs for Between operator."""
		handler = QueryRecordsHandler()
		start, end = handler._coerce_between_value("2026-03-01, 2026-03-05")
		self.assertEqual(start, "2026-03-01")
		self.assertEqual(end, "2026-03-05")

		# Single string value fallback
		start_single, end_single = handler._coerce_between_value("2026-03-01")
		self.assertEqual(start_single, "2026-03-01")
		self.assertEqual(end_single, "2026-03-01")

	def test_18_multi_depth_nested_logical_trees(self):
		"""Test 3-level deep nested logical tree: status='Open' AND (score >= 50 OR (enabled=1 AND score <= 10))."""
		tree_data = {
			"id": "root",
			"type": "group",
			"operator": "and",
			"children": [
				{
					"id": "node_1",
					"type": "leaf",
					"doctype": "QB Limit Parent",
					"field": "status",
					"operator": "=",
					"value": {"value": "Open", "value_type": "Value"},
				},
				{
					"id": "node_2",
					"type": "group",
					"operator": "or",
					"children": [
						{
							"id": "node_3",
							"type": "leaf",
							"doctype": "QB Limit Parent",
							"field": "score",
							"operator": ">=",
							"value": {"value": 50, "value_type": "Value"},
						},
						{
							"id": "node_4",
							"type": "group",
							"operator": "and",
							"children": [
								{
									"id": "node_5",
									"type": "leaf",
									"doctype": "QB Limit Parent",
									"field": "enabled",
									"operator": "=",
									"value": {"value": 1, "value_type": "Value"},
								},
								{
									"id": "node_6",
									"type": "leaf",
									"doctype": "QB Limit Parent",
									"field": "score",
									"operator": "<=",
									"value": {"value": 10, "value_type": "Value"},
								},
							],
						},
					],
				},
			],
		}

		handler = QueryRecordsHandler()
		backend_filters = handler._canonical_filter_tree_to_backend(tree_data, "QB Limit Parent")

		res = execute_query(
			doctype="QB Limit Parent",
			kwargs={"fields": ["name", "title"], "filters": backend_filters},
			ignore_permissions=True,
		)

		self.assertEqual(len(res), 1)
		self.assertEqual(res[0]["name"], self.p1.name)
