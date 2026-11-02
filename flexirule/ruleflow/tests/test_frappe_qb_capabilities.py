# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

import unittest
import uuid
from typing import ClassVar

import frappe
from frappe.query_builder.functions import Abs, Avg, Coalesce, Concat, Count, Extract, Max, Min, Now, Sum
from frappe.query_builder.utils import PseudoColumnMapper
from frappe.tests.utils import FrappeTestCase
from pypika import Field

from flexirule.ruleflow.tests.test_helpers import safe_cleanup_test_resources


class TestFrappeQBCapabilities(FrappeTestCase):
	"""
	Comprehensive, evidence-backed Backend Capability Audit for frappe.qb.get_query in Frappe v15.

	Tests all documented and undocumented capabilities of frappe.qb.get_query against
	the actual installed Frappe v15 / MariaDB environment.
	"""

	_created_doctypes: ClassVar[list[str]] = []
	_created_records: ClassVar[list[tuple[str, str]]] = []
	_run_id: ClassVar[str] = ""
	target_dt: ClassVar[str] = ""
	category_dt: ClassVar[str] = ""
	child_dt: ClassVar[str] = ""
	parent_dt: ClassVar[str] = ""
	tree_dt: ClassVar[str] = ""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls._created_doctypes = []
		cls._created_records = []
		cls.addClassCleanup(cls._cleanup_resources)
		cls._run_id = uuid.uuid4().hex[:8].upper()
		cls.target_dt = f"QB Target {cls._run_id}"
		cls.category_dt = f"QB Category {cls._run_id}"
		cls.child_dt = f"QB Child {cls._run_id}"
		cls.parent_dt = f"QB Parent {cls._run_id}"
		cls.tree_dt = f"QB Tree {cls._run_id}"
		cls._setup_test_doctypes()
		cls._setup_test_records()

	@classmethod
	def _cleanup_resources(cls):
		try:
			safe_cleanup_test_resources(doctypes=cls._created_doctypes, records=cls._created_records)
		finally:
			cls._created_records.clear()
			cls._created_doctypes.clear()

	@classmethod
	def _setup_test_doctypes(cls):
		# 1. Target DocType 1 for Link relationships
		if not frappe.db.exists("DocType", cls.target_dt):
			frappe.get_doc(
				{
					"doctype": "DocType",
					"name": cls.target_dt,
					"module": "RuleFlow",
					"custom": 1,
					"fields": [
						{"fieldname": "target_name", "fieldtype": "Data", "label": "Target Name", "reqd": 1},
						{"fieldname": "territory", "fieldtype": "Data", "label": "Territory"},
					],
				}
			).insert(ignore_permissions=True)
			cls._created_doctypes.append(cls.target_dt)

		# 2. Target DocType 2 for Multiple Link relationships
		if not frappe.db.exists("DocType", cls.category_dt):
			frappe.get_doc(
				{
					"doctype": "DocType",
					"name": cls.category_dt,
					"module": "RuleFlow",
					"custom": 1,
					"fields": [
						{
							"fieldname": "category_name",
							"fieldtype": "Data",
							"label": "Category Name",
							"reqd": 1,
						},
						{"fieldname": "group_code", "fieldtype": "Data", "label": "Group Code"},
					],
				}
			).insert(ignore_permissions=True)
			cls._created_doctypes.append(cls.category_dt)

		# 3. Child Table DocType
		if not frappe.db.exists("DocType", cls.child_dt):
			frappe.get_doc(
				{
					"doctype": "DocType",
					"name": cls.child_dt,
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
			cls._created_doctypes.append(cls.child_dt)

		# 4. Parent DocType (with nullable_text field for null/set testing)
		if not frappe.db.exists("DocType", cls.parent_dt):
			frappe.get_doc(
				{
					"doctype": "DocType",
					"name": cls.parent_dt,
					"module": "RuleFlow",
					"custom": 1,
					"fields": [
						{"fieldname": "parent_title", "fieldtype": "Data", "label": "Title"},
						{"fieldname": "status", "fieldtype": "Data", "label": "Status"},
						{"fieldname": "enabled", "fieldtype": "Check", "label": "Enabled"},
						{"fieldname": "nullable_text", "fieldtype": "Data", "label": "Nullable Text"},
						{
							"fieldname": "target_link",
							"fieldtype": "Link",
							"options": cls.target_dt,
							"label": "Target Link",
						},
						{
							"fieldname": "category_link",
							"fieldtype": "Link",
							"options": cls.category_dt,
							"label": "Category Link",
						},
						{
							"fieldname": "items",
							"fieldtype": "Table",
							"options": cls.child_dt,
							"label": "Items",
						},
					],
				}
			).insert(ignore_permissions=True)
			cls._created_doctypes.append(cls.parent_dt)

		# 5. Tree DocType for Hierarchy testing
		nsm_field = f"parent_qb_test_tree_{cls._run_id.lower()}"
		if not frappe.db.exists("DocType", cls.tree_dt):
			frappe.get_doc(
				{
					"doctype": "DocType",
					"name": cls.tree_dt,
					"module": "RuleFlow",
					"custom": 1,
					"is_tree": 1,
					"nsm_parent_field": nsm_field,
					"fields": [
						{"fieldname": "tree_name", "fieldtype": "Data", "label": "Tree Name", "reqd": 1},
						{
							"fieldname": nsm_field,
							"fieldtype": "Link",
							"options": cls.tree_dt,
							"label": "Parent QB Test Tree",
						},
						{"fieldname": "old_parent", "fieldtype": "Data", "label": "Old Parent"},
						{"fieldname": "is_group", "fieldtype": "Check", "label": "Is Group"},
						{"fieldname": "lft", "fieldtype": "Int", "label": "lft", "hidden": 1},
						{"fieldname": "rgt", "fieldtype": "Int", "label": "rgt", "hidden": 1},
					],
				}
			).insert(ignore_permissions=True)
			cls._created_doctypes.append(cls.tree_dt)

		# Commit required for dynamic DDL schema creation in Frappe so MariaDB table definitions
		# and DocType metadata are immediately visible across test query execution.
		frappe.db.commit()

	@classmethod
	def _setup_test_records(cls):
		cls.target1 = frappe.get_doc(
			{"doctype": cls.target_dt, "target_name": "T1", "territory": "North"}
		).insert(ignore_permissions=True)
		cls._created_records.append((cls.target_dt, cls.target1.name))

		cls.target2 = frappe.get_doc(
			{"doctype": cls.target_dt, "target_name": "T2", "territory": "South"}
		).insert(ignore_permissions=True)
		cls._created_records.append((cls.target_dt, cls.target2.name))

		cls.cat1 = frappe.get_doc(
			{"doctype": cls.category_dt, "category_name": "Cat 1", "group_code": "GRP-A"}
		).insert(ignore_permissions=True)
		cls._created_records.append((cls.category_dt, cls.cat1.name))

		cls.cat2 = frappe.get_doc(
			{"doctype": cls.category_dt, "category_name": "Cat 2", "group_code": "GRP-B"}
		).insert(ignore_permissions=True)
		cls._created_records.append((cls.category_dt, cls.cat2.name))

		# P1: nullable_text="A", target_link=T1, category_link=Cat1, two duplicate ITEM-001 rows
		cls.p1 = frappe.get_doc(
			{
				"doctype": cls.parent_dt,
				"parent_title": "P1",
				"status": "Open",
				"enabled": 1,
				"nullable_text": "A",
				"target_link": cls.target1.name,
				"category_link": cls.cat1.name,
				"items": [
					{"item_code": "ITEM-001", "qty": 2, "rate": 10, "amount": 20},
					{"item_code": "ITEM-001", "qty": 3, "rate": 10, "amount": 30},
					{"item_code": "ITEM-002", "qty": 5, "rate": 20, "amount": 100},
				],
			}
		).insert(ignore_permissions=True)
		cls._created_records.append((cls.parent_dt, cls.p1.name))

		# P2: nullable_text=None, target_link=T2, category_link=Cat2
		cls.p2 = frappe.get_doc(
			{
				"doctype": cls.parent_dt,
				"parent_title": "P2",
				"status": "Pending",
				"enabled": 1,
				"nullable_text": None,
				"target_link": cls.target2.name,
				"category_link": cls.cat2.name,
				"items": [{"item_code": "ITEM-001", "qty": 1, "rate": 10, "amount": 10}],
			}
		).insert(ignore_permissions=True)
		cls._created_records.append((cls.parent_dt, cls.p2.name))

		# P3: nullable_text="C", target_link=None, category_link=None
		cls.p3 = frappe.get_doc(
			{
				"doctype": cls.parent_dt,
				"parent_title": "P3",
				"status": "Closed",
				"enabled": 0,
				"nullable_text": "C",
				"target_link": None,
				"category_link": None,
				"items": [],
			}
		).insert(ignore_permissions=True)
		cls._created_records.append((cls.parent_dt, cls.p3.name))

		# Tree Hierarchy Setup
		cls.root = frappe.get_doc({"doctype": cls.tree_dt, "tree_name": "Root", "is_group": 1}).insert(
			ignore_permissions=True
		)
		cls._created_records.append((cls.tree_dt, cls.root.name))

		nsm_field = f"parent_qb_test_tree_{cls._run_id.lower()}"
		cls.child_a = frappe.get_doc(
			{
				"doctype": cls.tree_dt,
				"tree_name": "Child A",
				nsm_field: cls.root.name,
				"is_group": 1,
			}
		).insert(ignore_permissions=True)
		cls._created_records.append((cls.tree_dt, cls.child_a.name))

		cls.grandchild_a = frappe.get_doc(
			{
				"doctype": cls.tree_dt,
				"tree_name": "Grandchild A",
				nsm_field: cls.child_a.name,
				"is_group": 0,
			}
		).insert(ignore_permissions=True)
		cls._created_records.append((cls.tree_dt, cls.grandchild_a.name))

		cls.child_b = frappe.get_doc(
			{
				"doctype": cls.tree_dt,
				"tree_name": "Child B",
				nsm_field: cls.root.name,
				"is_group": 0,
			}
		).insert(ignore_permissions=True)
		cls._created_records.append((cls.tree_dt, cls.child_b.name))

	# -------------------------------------------------------------------------
	# 1. Basic get_query() Behavior & Fields
	# -------------------------------------------------------------------------
	def test_01_basic_get_query_and_fields(self):
		q = frappe.qb.get_query(self.parent_dt)
		sql = q.get_sql()
		self.assertIn("SELECT", sql)
		self.assertIn(f"`tab{self.parent_dt}`", sql)

		q_fields = frappe.qb.get_query(self.parent_dt, fields=["name", "status"])
		res_dict = q_fields.run(as_dict=True)
		self.assertIsInstance(res_dict, list)
		self.assertEqual(len(res_dict), 3)
		self.assertEqual({r["name"] for r in res_dict}, {self.p1.name, self.p2.name, self.p3.name})

		q_str = frappe.qb.get_query(self.parent_dt, fields="name, status")
		res_str = q_str.run(as_dict=True)
		self.assertEqual(len(res_str), len(res_dict))

		q_star = frappe.qb.get_query(self.parent_dt, fields="*")
		res_star = q_star.run(as_dict=True)
		self.assertIn("parent_title", res_star[0])
		self.assertIn("creation", res_star[0])

		q_alias = frappe.qb.get_query(self.parent_dt, fields=["name as doc_id", "status as state"])
		res_alias = q_alias.run(as_dict=True)
		self.assertIn("doc_id", res_alias[0])
		self.assertIn("state", res_alias[0])

	def test_02_execution_modes_and_iterators(self):
		q = frappe.qb.get_query(self.parent_dt, fields=["name", "status"], limit=2)

		res_default = q.run()
		self.assertIsInstance(res_default, (tuple, list))
		self.assertEqual(len(res_default), 2)

		res_dict = q.run(as_dict=True)
		self.assertIsInstance(res_dict, list)
		self.assertIsInstance(res_dict[0], dict)

		res_list = q.run(as_list=True)
		self.assertIsInstance(res_list, (tuple, list))

		q_pluck = frappe.qb.get_query(self.parent_dt, fields=["name"], limit=2)
		res_pluck = q_pluck.run(pluck=True)
		self.assertIsInstance(res_pluck, (tuple, list))
		self.assertIsInstance(res_pluck[0], str)

		# Iterator execution tests
		q_iter_dict = frappe.qb.get_query(self.parent_dt, fields=["name", "status"])
		it_dict = q_iter_dict.run(as_dict=True, as_iterator=True)
		self.assertTrue(hasattr(it_dict, "__next__") or hasattr(it_dict, "__iter__"))
		dict_rows = [row for row in it_dict]
		self.assertEqual(len(dict_rows), 3)
		self.assertIsInstance(dict_rows[0], dict)
		self.assertEqual({r["name"] for r in dict_rows}, {self.p1.name, self.p2.name, self.p3.name})

		q_iter_list = frappe.qb.get_query(self.parent_dt, fields=["name", "status"])
		it_list = q_iter_list.run(as_list=True, as_iterator=True)
		list_rows = [row for row in it_list]
		self.assertEqual(len(list_rows), 3)
		self.assertIsInstance(list_rows[0], (tuple, list))

	# -------------------------------------------------------------------------
	# 2. Filter Syntax & Null/Set Semantics
	# -------------------------------------------------------------------------
	def test_03_filter_forms_and_logic(self):
		q1 = frappe.qb.get_query(self.parent_dt, filters={"status": "Open"})
		res1 = q1.run(as_dict=True)
		self.assertEqual({r["name"] for r in res1}, {self.p1.name})

		q2 = frappe.qb.get_query(self.parent_dt, filters={"enabled": [">", 0]})
		res2 = q2.run(as_dict=True)
		self.assertEqual({r["name"] for r in res2}, {self.p1.name, self.p2.name})

		q3 = frappe.qb.get_query(self.parent_dt, filters=[["status", "=", "Open"]])
		res3 = q3.run(as_dict=True)
		self.assertEqual({r["name"] for r in res3}, {self.p1.name})

		# String "or" in list filters is broken in Engine.apply_filters
		q_or = frappe.qb.get_query(
			self.parent_dt, filters=[["status", "=", "Open"], "or", ["status", "=", "Pending"]]
		)
		res_or = q_or.run(as_dict=True)
		self.assertEqual(len(res_or), 0)

		# Working Pypika OR logic
		t = frappe.qb.DocType(self.parent_dt)
		q_pypika_or = frappe.qb.get_query(
			self.parent_dt, filters=(t.status == "Open") | (t.status == "Pending")
		)
		res_pypika_or = q_pypika_or.run(as_dict=True)
		self.assertEqual({r["name"] for r in res_pypika_or}, {self.p1.name, self.p2.name})

	def test_04_nested_and_or_semantics(self):
		t = frappe.qb.DocType(self.parent_dt)

		# Structure 1: (status = Open AND enabled = 1) OR (status = Pending AND enabled = 1)
		crit1 = ((t.status == "Open") & (t.enabled == 1)) | ((t.status == "Pending") & (t.enabled == 1))
		q1 = frappe.qb.get_query(self.parent_dt, filters=crit1)
		res1 = q1.run(as_dict=True)
		self.assertEqual({r["name"] for r in res1}, {self.p1.name, self.p2.name})

		# Structure 2: status = Open AND (enabled = 1 OR status = Pending)
		crit2 = (t.status == "Open") & ((t.enabled == 1) | (t.status == "Pending"))
		q2 = frappe.qb.get_query(self.parent_dt, filters=crit2)
		res2 = q2.run(as_dict=True)
		self.assertEqual({r["name"] for r in res2}, {self.p1.name})

	def test_05_null_set_operator_semantics(self):
		# P1: nullable_text="A", P2: nullable_text=None, P3: nullable_text="C"
		q_is_set = frappe.qb.get_query(self.parent_dt, filters=[["nullable_text", "is", "set"]])
		res_is_set = q_is_set.run(as_dict=True)
		self.assertEqual({r["name"] for r in res_is_set}, {self.p1.name, self.p3.name})

		q_is_not_set = frappe.qb.get_query(self.parent_dt, filters=[["nullable_text", "is", "not set"]])
		res_is_not_set = q_is_not_set.run(as_dict=True)
		self.assertEqual({r["name"] for r in res_is_not_set}, {self.p2.name})

	def test_06_tree_operators_on_tree_doctype(self):
		q_desc = frappe.qb.get_query(
			self.tree_dt,
			fields=["name", "tree_name"],
			filters=[["name", "descendants of", self.root.name]],
		)
		res_desc = q_desc.run(as_dict=True)
		self.assertEqual({r["tree_name"] for r in res_desc}, {"Child A", "Grandchild A", "Child B"})

		q_anc = frappe.qb.get_query(
			self.tree_dt,
			fields=["name", "tree_name"],
			filters=[["name", "ancestors of", self.grandchild_a.name]],
		)
		res_anc = q_anc.run(as_dict=True)
		self.assertEqual({r["tree_name"] for r in res_anc}, {"Root", "Child A"})

	# -------------------------------------------------------------------------
	# 3. Link-Field Traversal
	# -------------------------------------------------------------------------
	def test_07_link_field_traversal_and_ordering(self):
		# Selection across multiple linked tables
		q = frappe.qb.get_query(
			self.parent_dt, fields=["name", "target_link.territory", "category_link.group_code"]
		)
		sql = q.get_sql()
		self.assertIn(f"LEFT JOIN `tab{self.target_dt}`", sql)
		self.assertIn(f"LEFT JOIN `tab{self.category_dt}`", sql)
		res = q.run(as_dict=True)
		p1_res = next(r for r in res if r["name"] == self.p1.name)
		self.assertEqual(p1_res.get("territory"), "North")
		self.assertEqual(p1_res.get("group_code"), "GRP-A")

		# Filtering across multiple links
		q_filter = frappe.qb.get_query(
			self.parent_dt, filters={"target_link.territory": "North", "category_link.group_code": "GRP-A"}
		)
		res_filter = q_filter.run(as_dict=True)
		self.assertEqual({r["name"] for r in res_filter}, {self.p1.name})

		# String path order_by fails due to join alias unmapping in Engine.apply_order_by
		with self.assertRaises(Exception):
			frappe.qb.get_query(
				self.parent_dt,
				fields=["name", "target_link.territory"],
				order_by="target_link.territory asc",
			).run(as_dict=True)

		# Pypika explicit join & ordering succeeds
		target_tbl = frappe.qb.DocType(self.target_dt)
		parent_tbl = frappe.qb.DocType(self.parent_dt)
		q_pypika_order = (
			frappe.qb.from_(parent_tbl)
			.left_join(target_tbl)
			.on(parent_tbl.target_link == target_tbl.name)
			.select(parent_tbl.name, target_tbl.territory)
			.orderby(target_tbl.territory)
		)
		res_pypika_order = q_pypika_order.run(as_dict=True)
		self.assertEqual(len(res_pypika_order), 3)

	# -------------------------------------------------------------------------
	# 4. Child Table Traversal vs Structured Child Fetching
	# -------------------------------------------------------------------------
	def test_08_child_table_traversal_vs_structured(self):
		# Flat child traversal: 1 query, LEFT JOIN, row duplication per child item
		q_flat = frappe.qb.get_query(self.parent_dt, fields=["name", "items.item_code"])
		res_flat = q_flat.run(as_dict=True)
		p1_flat = [r for r in res_flat if r["name"] == self.p1.name]
		self.assertEqual(len(p1_flat), 3)  # P1 has 3 child records

		# Structured child fetching: 2 queries (parent query + ChildQuery sub-query), distinct parent dicts
		q_struct = frappe.qb.get_query(self.parent_dt, fields=["name", {"items": ["item_code", "qty"]}])
		res_struct = q_struct.run(as_dict=True)
		self.assertEqual(len(res_struct), 3)  # 3 distinct parent dicts
		p1_struct = next(r for r in res_struct if r["name"] == self.p1.name)
		self.assertEqual(len(p1_struct["items"]), 3)

	def test_09_distinct_semantics(self):
		# Duplicate child records for P1 (2 x ITEM-001)
		q_dup = frappe.qb.get_query(self.parent_dt, fields=["name"], filters={"items.item_code": "ITEM-001"})
		res_dup = q_dup.run(as_dict=True)
		p1_dup_count = sum(1 for r in res_dup if r["name"] == self.p1.name)
		self.assertEqual(p1_dup_count, 2)

		# distinct=True deduplicates parent rows when only parent fields are selected
		q_dist = frappe.qb.get_query(
			self.parent_dt, fields=["name"], filters={"items.item_code": "ITEM-001"}, distinct=True
		)
		res_dist = q_dist.run(as_dict=True)
		self.assertEqual({r["name"] for r in res_dist}, {self.p1.name, self.p2.name})
		self.assertEqual(len(res_dist), 2)

	def test_10_child_doctype_as_root_query(self):
		# Querying Child DocType directly
		q_child = frappe.qb.get_query(
			self.child_dt, fields=["name", "item_code", "qty", "parent", "parenttype", "parentfield"]
		)
		sql_child = q_child.get_sql()
		self.assertIn(f"FROM `tab{self.child_dt}`", sql_child)
		res_child = q_child.run(as_dict=True)
		self.assertEqual(len(res_child), 4)
		self.assertTrue(all("parent" in r and "parenttype" in r for r in res_child))

		# Filtering child records by parent context
		q_child_p1 = frappe.qb.get_query(
			self.child_dt,
			fields=["name", "item_code"],
			filters=[["parent", "=", self.p1.name], ["parenttype", "=", self.parent_dt]],
		)
		res_child_p1 = q_child_p1.run(as_dict=True)
		self.assertEqual(len(res_child_p1), 3)

		# Engine.get_query rejects parent_doctype kwarg
		with self.assertRaises(TypeError):
			frappe.qb.get_query(self.child_dt, parent_doctype=self.parent_dt)

	# -------------------------------------------------------------------------
	# 5. Aggregation Functions & Scalar Functions
	# -------------------------------------------------------------------------
	def test_11_aggregation_functions(self):
		with self.assertRaises(AttributeError):
			frappe.qb.get_query(self.parent_dt, fields=[{"COUNT": "name", "as": "total_count"}])

		q_count_str = frappe.qb.get_query(self.parent_dt, fields=["count(name) as total_count"])
		res_count_str = q_count_str.run(as_dict=True)
		self.assertEqual(res_count_str[0]["total_count"], 3)

		# Pypika functions: Count, Sum, Avg, Min, Max
		t = frappe.qb.DocType(self.parent_dt)
		q_agg = frappe.qb.get_query(
			self.parent_dt,
			fields=[
				Count(t.name).as_("total"),
				Sum(t.enabled).as_("sum_enabled"),
				Avg(t.enabled).as_("avg_enabled"),
				Min(t.status).as_("min_status"),
				Max(t.status).as_("max_status"),
			],
		)
		res_agg = q_agg.run(as_dict=True)
		self.assertEqual(res_agg[0]["total"], 3)
		self.assertEqual(res_agg[0]["sum_enabled"], 2)

		# Dotted child sum in raw string field raises OperationalError because Engine string parser does not auto-join child tables for function strings
		with self.assertRaises(Exception):
			frappe.qb.get_query(
				self.parent_dt, fields=["name", "sum(items.qty) as total_qty"], group_by="name"
			).run(as_dict=True)

		# Pypika explicit child join calculates child Sum(child.qty) accurately
		parent_tbl = frappe.qb.DocType(self.parent_dt)
		child_tbl = frappe.qb.DocType(self.child_dt)
		q_pypika_child_sum = (
			frappe.qb.from_(parent_tbl)
			.left_join(child_tbl)
			.on((child_tbl.parent == parent_tbl.name) & (child_tbl.parenttype == self.parent_dt))
			.select(parent_tbl.name, Sum(child_tbl.qty).as_("total_qty"))
			.groupby(parent_tbl.name)
		)
		res_pypika_child_sum = q_pypika_child_sum.run(as_dict=True)
		p1_sum = next(r for r in res_pypika_child_sum if r["name"] == self.p1.name)
		self.assertEqual(p1_sum["total_qty"], 10.0)  # 2 + 3 + 5 = 10

	def test_12_scalar_functions(self):
		with self.assertRaises(AttributeError):
			frappe.qb.get_query(
				self.parent_dt, fields=["name", {"IFNULL": ["target_link", "'None'"], "as": "safe_link"}]
			)

		# String function "now() as current_time" is unsupported due to string parser field lookup
		with self.assertRaises(Exception):
			frappe.qb.get_query(self.parent_dt, fields=["now() as current_time"], limit=1).run(as_dict=True)

		# Pypika functions: Now, Coalesce, Concat, Abs, Extract
		q_now = frappe.qb.get_query(self.parent_dt, fields=[Now().as_("current_time")], limit=1)
		res_now = q_now.run(as_dict=True)
		self.assertIn("current_time", res_now[0])

		target_col = PseudoColumnMapper(f"`tab{self.parent_dt}`.`target_link`")
		q_coalesce = frappe.qb.get_query(
			self.parent_dt, fields=["name", Coalesce(target_col, "'None'").as_("safe_target")]
		)
		res_coalesce = q_coalesce.run(as_dict=True)
		p3_coalesce = next(r for r in res_coalesce if r["name"] == self.p3.name)
		self.assertEqual(p3_coalesce["safe_target"], "'None'")

		t = frappe.qb.DocType(self.parent_dt)
		q_concat = frappe.qb.get_query(
			self.parent_dt, fields=[Concat(t.status, " - ", t.parent_title).as_("full_label")]
		)
		res_concat = q_concat.run(as_dict=True)
		self.assertTrue(any("Open - P1" in str(r.get("full_label")) for r in res_concat))

	# -------------------------------------------------------------------------
	# 6. Record Locking, Permissions & Security
	# -------------------------------------------------------------------------
	def test_13_record_locking_and_transactions(self):
		frappe.db.savepoint("test_record_lock")

		q_lock1 = frappe.qb.get_query(
			self.parent_dt, fields=["name"], limit=1, for_update=True, skip_locked=True
		)
		sql_lock1 = q_lock1.get_sql()
		self.assertIn("FOR UPDATE SKIP LOCKED", sql_lock1)
		res1 = q_lock1.run(as_dict=True)
		self.assertIsInstance(res1, list)

		q_lock2 = frappe.qb.get_query(self.parent_dt, fields=["name"], limit=1, for_update=True, wait=False)
		sql_lock2 = q_lock2.get_sql()
		self.assertIn("FOR UPDATE NOWAIT", sql_lock2)
		res2 = q_lock2.run(as_dict=True)
		self.assertIsInstance(res2, list)

		frappe.db.rollback(save_point="test_record_lock")

	def test_14_permissions_and_security(self):
		with self.assertRaises(TypeError):
			frappe.qb.get_query(self.parent_dt, ignore_permissions=True)

		with self.assertRaises(TypeError):
			frappe.qb.get_query(self.parent_dt, user="Administrator")

		from frappe.database.query import Permission

		q = frappe.qb.get_query(self.parent_dt, fields=["name"])
		Permission.check_permissions(q, user="Administrator")

		# Permission check for child query with parent_doctype parameter
		q_child = frappe.qb.get_query(self.child_dt, fields=["name"])
		Permission.check_permissions(q_child, user="Administrator", parent_doctype=self.parent_dt)

		# Invalid column raises OperationalError
		with self.assertRaises(Exception):
			frappe.qb.get_query(self.parent_dt, fields=["non_existent_col"]).run(as_dict=True)
