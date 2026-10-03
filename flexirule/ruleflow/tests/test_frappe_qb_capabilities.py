# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

import unittest

import frappe
from frappe.query_builder.functions import Coalesce, Count, Max, Min, Now, Sum
from frappe.query_builder.utils import PseudoColumnMapper
from frappe.tests.utils import FrappeTestCase
from pypika import Field


class TestFrappeQBCapabilities(FrappeTestCase):
	"""
	Comprehensive, evidence-backed Backend Capability Audit for frappe.qb.get_query in Frappe v15.

	Tests all documented and undocumented capabilities of frappe.qb.get_query against
	the actual installed Frappe v15 / MariaDB environment.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls._setup_test_doctypes()
		cls._setup_test_records()

	@classmethod
	def tearDownClass(cls):
		frappe.db.delete("QB Test Child")
		frappe.db.delete("QB Test Parent")
		frappe.db.delete("QB Test Target")
		frappe.db.delete("QB Test Category")
		frappe.db.delete("QB Test Tree")

		for dt in ["QB Test Parent", "QB Test Child", "QB Test Target", "QB Test Category", "QB Test Tree"]:
			if frappe.db.exists("DocType", dt):
				frappe.delete_doc("DocType", dt, force=True, ignore_permissions=True)

		frappe.db.commit()
		super().tearDownClass()

	@classmethod
	def _setup_test_doctypes(cls):
		# 1. Target DocType 1 for Link relationships
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

		# 2. Target DocType 2 for Multiple Link relationships
		if not frappe.db.exists("DocType", "QB Test Category"):
			frappe.get_doc(
				{
					"doctype": "DocType",
					"name": "QB Test Category",
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

		# 3. Child Table DocType
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

		# 4. Parent DocType
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
							"fieldname": "category_link",
							"fieldtype": "Link",
							"options": "QB Test Category",
							"label": "Category Link",
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

		# 5. Tree DocType for Hierarchy testing
		if not frappe.db.exists("DocType", "QB Test Tree"):
			frappe.get_doc(
				{
					"doctype": "DocType",
					"name": "QB Test Tree",
					"module": "RuleFlow",
					"custom": 1,
					"is_tree": 1,
					"nsm_parent_field": "parent_qb_test_tree",
					"fields": [
						{"fieldname": "tree_name", "fieldtype": "Data", "label": "Tree Name", "reqd": 1},
						{
							"fieldname": "parent_qb_test_tree",
							"fieldtype": "Link",
							"options": "QB Test Tree",
							"label": "Parent QB Test Tree",
						},
						{"fieldname": "old_parent", "fieldtype": "Data", "label": "Old Parent"},
						{"fieldname": "is_group", "fieldtype": "Check", "label": "Is Group"},
						{"fieldname": "lft", "fieldtype": "Int", "label": "lft", "hidden": 1},
						{"fieldname": "rgt", "fieldtype": "Int", "label": "rgt", "hidden": 1},
					],
				}
			).insert(ignore_permissions=True)

		frappe.db.commit()

	@classmethod
	def _setup_test_records(cls):
		frappe.db.delete("QB Test Child")
		frappe.db.delete("QB Test Parent")
		frappe.db.delete("QB Test Target")
		frappe.db.delete("QB Test Category")
		frappe.db.delete("QB Test Tree")

		cls.target1 = frappe.get_doc(
			{"doctype": "QB Test Target", "target_name": "T1", "territory": "North"}
		).insert(ignore_permissions=True)
		cls.target2 = frappe.get_doc(
			{"doctype": "QB Test Target", "target_name": "T2", "territory": "South"}
		).insert(ignore_permissions=True)

		cls.cat1 = frappe.get_doc(
			{"doctype": "QB Test Category", "category_name": "Cat 1", "group_code": "GRP-A"}
		).insert(ignore_permissions=True)
		cls.cat2 = frappe.get_doc(
			{"doctype": "QB Test Category", "category_name": "Cat 2", "group_code": "GRP-B"}
		).insert(ignore_permissions=True)

		# P1 has two duplicate ITEM-001 rows for testing deduplication
		cls.p1 = frappe.get_doc(
			{
				"doctype": "QB Test Parent",
				"parent_title": "P1",
				"status": "Open",
				"enabled": 1,
				"target_link": cls.target1.name,
				"category_link": cls.cat1.name,
				"items": [
					{"item_code": "ITEM-001", "qty": 2, "rate": 10, "amount": 20},
					{"item_code": "ITEM-001", "qty": 3, "rate": 10, "amount": 30},
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
				"category_link": cls.cat2.name,
				"items": [{"item_code": "ITEM-001", "qty": 1, "rate": 10, "amount": 10}],
			}
		).insert(ignore_permissions=True)

		cls.p3 = frappe.get_doc(
			{
				"doctype": "QB Test Parent",
				"parent_title": "P3",
				"status": "Closed",
				"enabled": 0,
				"target_link": None,
				"category_link": None,
				"items": [],
			}
		).insert(ignore_permissions=True)

		# Tree Hierarchy Setup
		cls.root = frappe.get_doc({"doctype": "QB Test Tree", "tree_name": "Root", "is_group": 1}).insert(
			ignore_permissions=True
		)
		cls.child_a = frappe.get_doc(
			{
				"doctype": "QB Test Tree",
				"tree_name": "Child A",
				"parent_qb_test_tree": cls.root.name,
				"is_group": 1,
			}
		).insert(ignore_permissions=True)
		cls.grandchild_a = frappe.get_doc(
			{
				"doctype": "QB Test Tree",
				"tree_name": "Grandchild A",
				"parent_qb_test_tree": cls.child_a.name,
				"is_group": 0,
			}
		).insert(ignore_permissions=True)
		cls.child_b = frappe.get_doc(
			{
				"doctype": "QB Test Tree",
				"tree_name": "Child B",
				"parent_qb_test_tree": cls.root.name,
				"is_group": 0,
			}
		).insert(ignore_permissions=True)

		frappe.db.commit()

	# -------------------------------------------------------------------------
	# 1. Basic get_query() Behavior & Fields
	# -------------------------------------------------------------------------
	def test_01_basic_get_query_and_fields(self):
		q = frappe.qb.get_query("QB Test Parent")
		sql = q.get_sql()
		self.assertIn("SELECT", sql)
		self.assertIn("`tabQB Test Parent`", sql)

		q_fields = frappe.qb.get_query("QB Test Parent", fields=["name", "status"])
		res_dict = q_fields.run(as_dict=True)
		self.assertIsInstance(res_dict, list)
		self.assertEqual(len(res_dict), 3)
		self.assertEqual({r["name"] for r in res_dict}, {self.p1.name, self.p2.name, self.p3.name})

		q_str = frappe.qb.get_query("QB Test Parent", fields="name, status")
		res_str = q_str.run(as_dict=True)
		self.assertEqual(len(res_str), len(res_dict))

		q_star = frappe.qb.get_query("QB Test Parent", fields="*")
		res_star = q_star.run(as_dict=True)
		self.assertIn("parent_title", res_star[0])
		self.assertIn("creation", res_star[0])

		q_alias = frappe.qb.get_query("QB Test Parent", fields=["name as doc_id", "status as state"])
		res_alias = q_alias.run(as_dict=True)
		self.assertIn("doc_id", res_alias[0])
		self.assertIn("state", res_alias[0])

	def test_02_execution_modes_and_iterators(self):
		q = frappe.qb.get_query("QB Test Parent", fields=["name", "status"], limit=2)

		res_default = q.run()
		self.assertIsInstance(res_default, (tuple, list))
		self.assertEqual(len(res_default), 2)

		res_dict = q.run(as_dict=True)
		self.assertIsInstance(res_dict, list)
		self.assertIsInstance(res_dict[0], dict)

		res_list = q.run(as_list=True)
		self.assertIsInstance(res_list, (tuple, list))

		q_pluck = frappe.qb.get_query("QB Test Parent", fields=["name"], limit=2)
		res_pluck = q_pluck.run(pluck=True)
		self.assertIsInstance(res_pluck, (tuple, list))
		self.assertIsInstance(res_pluck[0], str)

		# 5. Iterator execution tests
		q_iter_dict = frappe.qb.get_query("QB Test Parent", fields=["name", "status"])
		it_dict = q_iter_dict.run(as_dict=True, as_iterator=True)
		self.assertTrue(hasattr(it_dict, "__next__") or hasattr(it_dict, "__iter__"))
		dict_rows = [row for row in it_dict]
		self.assertEqual(len(dict_rows), 3)
		self.assertIsInstance(dict_rows[0], dict)

		q_iter_list = frappe.qb.get_query("QB Test Parent", fields=["name", "status"])
		it_list = q_iter_list.run(as_list=True, as_iterator=True)
		list_rows = [row for row in it_list]
		self.assertEqual(len(list_rows), 3)
		self.assertIsInstance(list_rows[0], (tuple, list))

	# -------------------------------------------------------------------------
	# 2. Filter Syntax & Logical Operations
	# -------------------------------------------------------------------------
	def test_03_filter_forms_and_logic(self):
		q1 = frappe.qb.get_query("QB Test Parent", filters={"status": "Open"})
		res1 = q1.run(as_dict=True)
		self.assertEqual({r["name"] for r in res1}, {self.p1.name})

		q2 = frappe.qb.get_query("QB Test Parent", filters={"enabled": [">", 0]})
		res2 = q2.run(as_dict=True)
		self.assertEqual({r["name"] for r in res2}, {self.p1.name, self.p2.name})

		q3 = frappe.qb.get_query("QB Test Parent", filters=[["status", "=", "Open"]])
		res3 = q3.run(as_dict=True)
		self.assertEqual({r["name"] for r in res3}, {self.p1.name})

		# String "or" in list filters is broken in Engine.apply_filters
		q_or = frappe.qb.get_query(
			"QB Test Parent", filters=[["status", "=", "Open"], "or", ["status", "=", "Pending"]]
		)
		res_or = q_or.run(as_dict=True)
		self.assertEqual(len(res_or), 0)

		# Working Pypika OR logic
		t = frappe.qb.DocType("QB Test Parent")
		q_pypika_or = frappe.qb.get_query(
			"QB Test Parent", filters=(t.status == "Open") | (t.status == "Pending")
		)
		res_pypika_or = q_pypika_or.run(as_dict=True)
		self.assertEqual({r["name"] for r in res_pypika_or}, {self.p1.name, self.p2.name})

	def test_04_nested_and_or_semantics(self):
		t = frappe.qb.DocType("QB Test Parent")

		# Structure 1: (status = Open AND enabled = 1) OR (status = Pending AND enabled = 1)
		crit1 = ((t.status == "Open") & (t.enabled == 1)) | ((t.status == "Pending") & (t.enabled == 1))
		q1 = frappe.qb.get_query("QB Test Parent", filters=crit1)
		res1 = q1.run(as_dict=True)
		self.assertEqual({r["name"] for r in res1}, {self.p1.name, self.p2.name})

		# Structure 2: status = Open AND (enabled = 1 OR status = Pending)
		crit2 = (t.status == "Open") & ((t.enabled == 1) | (t.status == "Pending"))
		q2 = frappe.qb.get_query("QB Test Parent", filters=crit2)
		res2 = q2.run(as_dict=True)
		self.assertEqual({r["name"] for r in res2}, {self.p1.name})

	def test_05_filter_operators(self):
		ops_to_test = [
			("=", "Open", {self.p1.name}),
			("!=", "Open", {self.p2.name, self.p3.name}),
			(">", 0, {self.p1.name, self.p2.name}),
			("<", 1, {self.p3.name}),
			(">=", 1, {self.p1.name, self.p2.name}),
			("<=", 0, {self.p3.name}),
			("like", "%pe%", {self.p1.name, self.p2.name}),
			("not like", "%pe%", {self.p3.name}),
			("in", ["Open", "Pending"], {self.p1.name, self.p2.name}),
			("not in", ["Open", "Pending"], {self.p3.name}),
			("is", "set", {self.p1.name, self.p2.name, self.p3.name}),
			("is", "not set", set()),
		]

		for op, val, expected_names in ops_to_test:
			with self.subTest(op=op, val=val):
				q = frappe.qb.get_query(
					"QB Test Parent",
					filters=[["status" if op not in (">", "<", ">=", "<=") else "enabled", op, val]],
				)
				res = q.run(as_dict=True)
				self.assertEqual(
					{r["name"] for r in res},
					expected_names,
					f"Failed for op '{op}' with val '{val}'. Got {{r['name'] for r in res}}, expected {expected_names}",
				)

	def test_06_tree_operators_on_tree_doctype(self):
		# Tree operators on a valid is_tree=1 DocType
		q_desc = frappe.qb.get_query(
			"QB Test Tree",
			fields=["name", "tree_name"],
			filters=[["name", "descendants of", self.root.name]],
		)
		res_desc = q_desc.run(as_dict=True)
		self.assertEqual({r["tree_name"] for r in res_desc}, {"Child A", "Grandchild A", "Child B"})

		q_anc = frappe.qb.get_query(
			"QB Test Tree",
			fields=["name", "tree_name"],
			filters=[["name", "ancestors of", self.grandchild_a.name]],
		)
		res_anc = q_anc.run(as_dict=True)
		self.assertEqual({r["tree_name"] for r in res_anc}, {"Root", "Child A"})

	# -------------------------------------------------------------------------
	# 3. Link-Field Traversal
	# -------------------------------------------------------------------------
	def test_07_link_field_traversal(self):
		# Selection
		q = frappe.qb.get_query(
			"QB Test Parent", fields=["name", "target_link.territory", "category_link.group_code"]
		)
		sql = q.get_sql()
		self.assertIn("LEFT JOIN `tabQB Test Target`", sql)
		self.assertIn("LEFT JOIN `tabQB Test Category`", sql)
		res = q.run(as_dict=True)
		p1_res = next(r for r in res if r["name"] == self.p1.name)
		self.assertEqual(p1_res.get("territory"), "North")
		self.assertEqual(p1_res.get("group_code"), "GRP-A")

		# Filtering
		q_filter = frappe.qb.get_query(
			"QB Test Parent", filters={"target_link.territory": "North", "category_link.group_code": "GRP-A"}
		)
		res_filter = q_filter.run(as_dict=True)
		self.assertEqual({r["name"] for r in res_filter}, {self.p1.name})

		# String path order_by fails due to join alias unmapping in Engine.apply_order_by
		with self.assertRaises(Exception):
			frappe.qb.get_query(
				"QB Test Parent",
				fields=["name", "target_link.territory"],
				order_by="target_link.territory asc",
			).run(as_dict=True)

		# Pypika join & ordering succeeds
		target_tbl = frappe.qb.DocType("QB Test Target")
		parent_tbl = frappe.qb.DocType("QB Test Parent")
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
		# Flat child traversal
		q_flat = frappe.qb.get_query("QB Test Parent", fields=["name", "items.item_code"])
		res_flat = q_flat.run(as_dict=True)
		p1_flat = [r for r in res_flat if r["name"] == self.p1.name]
		self.assertEqual(len(p1_flat), 3)  # 3 child rows for P1

		# Structured child fetching
		q_struct = frappe.qb.get_query("QB Test Parent", fields=["name", {"items": ["item_code", "qty"]}])
		res_struct = q_struct.run(as_dict=True)
		self.assertEqual(len(res_struct), 3)  # 3 distinct parent rows
		p1_struct = next(r for r in res_struct if r["name"] == self.p1.name)
		self.assertEqual(len(p1_struct["items"]), 3)

	def test_09_distinct_semantics(self):
		# P1 has two ITEM-001 rows and one ITEM-002 row
		q_dup = frappe.qb.get_query(
			"QB Test Parent", fields=["name"], filters={"items.item_code": "ITEM-001"}
		)
		res_dup = q_dup.run(as_dict=True)
		p1_dup_count = sum(1 for r in res_dup if r["name"] == self.p1.name)
		self.assertEqual(p1_dup_count, 2)

		# distinct=True deduplicates parent rows when only parent fields are selected
		q_dist = frappe.qb.get_query(
			"QB Test Parent", fields=["name"], filters={"items.item_code": "ITEM-001"}, distinct=True
		)
		res_dist = q_dist.run(as_dict=True)
		self.assertEqual({r["name"] for r in res_dist}, {self.p1.name, self.p2.name})
		self.assertEqual(len(res_dist), 2)

	def test_10_child_doctype_as_root_query(self):
		# Querying Child DocType directly
		q_child = frappe.qb.get_query(
			"QB Test Child", fields=["name", "item_code", "qty", "parent", "parenttype", "parentfield"]
		)
		sql_child = q_child.get_sql()
		self.assertIn("FROM `tabQB Test Child`", sql_child)
		res_child = q_child.run(as_dict=True)
		self.assertEqual(len(res_child), 4)
		self.assertTrue(all("parent" in r and "parenttype" in r for r in res_child))

		# Engine.get_query rejects parent_doctype kwarg
		with self.assertRaises(TypeError):
			frappe.qb.get_query("QB Test Child", parent_doctype="QB Test Parent")

	# -------------------------------------------------------------------------
	# 5. Aggregation Functions & Scalar Functions
	# -------------------------------------------------------------------------
	def test_11_aggregation_functions(self):
		with self.assertRaises(AttributeError):
			frappe.qb.get_query("QB Test Parent", fields=[{"COUNT": "name", "as": "total_count"}])

		q_count_str = frappe.qb.get_query("QB Test Parent", fields=["count(name) as total_count"])
		res_count_str = q_count_str.run(as_dict=True)
		self.assertEqual(res_count_str[0]["total_count"], 3)

		# Pypika functions
		t = frappe.qb.DocType("QB Test Parent")
		q_agg = frappe.qb.get_query(
			"QB Test Parent",
			fields=[
				Count(t.name).as_("total"),
				Sum(t.enabled).as_("sum_enabled"),
				Min(t.status).as_("min_status"),
				Max(t.status).as_("max_status"),
			],
		)
		res_agg = q_agg.run(as_dict=True)
		self.assertEqual(res_agg[0]["total"], 3)
		self.assertEqual(res_agg[0]["sum_enabled"], 2)

		# Dotted child sum in raw string field raises OperationalError because Engine string parser does not auto-join for function strings
		with self.assertRaises(Exception):
			frappe.qb.get_query(
				"QB Test Parent", fields=["name", "sum(items.qty) as total_qty"], group_by="name"
			).run(as_dict=True)

		# Pypika explicit child join calculates child Sum(child.qty) accurately
		parent_tbl = frappe.qb.DocType("QB Test Parent")
		child_tbl = frappe.qb.DocType("QB Test Child")
		q_pypika_child_sum = (
			frappe.qb.from_(parent_tbl)
			.left_join(child_tbl)
			.on((child_tbl.parent == parent_tbl.name) & (child_tbl.parenttype == "QB Test Parent"))
			.select(parent_tbl.name, Sum(child_tbl.qty).as_("total_qty"))
			.groupby(parent_tbl.name)
		)
		res_pypika_child_sum = q_pypika_child_sum.run(as_dict=True)
		p1_sum = next(r for r in res_pypika_child_sum if r["name"] == self.p1.name)
		self.assertEqual(p1_sum["total_qty"], 10.0)  # 2 + 3 + 5 = 10

	def test_12_scalar_functions(self):
		with self.assertRaises(AttributeError):
			frappe.qb.get_query(
				"QB Test Parent", fields=["name", {"IFNULL": ["target_link", "'None'"], "as": "safe_link"}]
			)

		# String function "now() as current_time" is unsupported due to string parser field lookup
		with self.assertRaises(Exception):
			frappe.qb.get_query("QB Test Parent", fields=["now() as current_time"], limit=1).run(as_dict=True)

		# Pypika Now() function succeeds
		q_now = frappe.qb.get_query("QB Test Parent", fields=[Now().as_("current_time")], limit=1)
		res_now = q_now.run(as_dict=True)
		self.assertIn("current_time", res_now[0])

		# Table-qualified column term for Coalesce / Ifnull evaluates NULL properly
		target_col = PseudoColumnMapper("`tabQB Test Parent`.`target_link`")
		q_coalesce = frappe.qb.get_query(
			"QB Test Parent", fields=["name", Coalesce(target_col, "'None'").as_("safe_target")]
		)
		res_coalesce = q_coalesce.run(as_dict=True)
		p3_coalesce = next(r for r in res_coalesce if r["name"] == self.p3.name)
		self.assertEqual(p3_coalesce["safe_target"], "'None'")

	# -------------------------------------------------------------------------
	# 6. Record Locking, Permissions & Debug
	# -------------------------------------------------------------------------
	def test_13_record_locking_and_transactions(self):
		frappe.db.begin()

		q_lock1 = frappe.qb.get_query(
			"QB Test Parent", fields=["name"], limit=1, for_update=True, skip_locked=True
		)
		sql_lock1 = q_lock1.get_sql()
		self.assertIn("FOR UPDATE SKIP LOCKED", sql_lock1)
		res1 = q_lock1.run(as_dict=True)
		self.assertIsInstance(res1, list)

		q_lock2 = frappe.qb.get_query("QB Test Parent", fields=["name"], limit=1, for_update=True, wait=False)
		sql_lock2 = q_lock2.get_sql()
		self.assertIn("FOR UPDATE NOWAIT", sql_lock2)
		res2 = q_lock2.run(as_dict=True)
		self.assertIsInstance(res2, list)

		frappe.db.rollback()

	def test_14_permissions_and_security(self):
		with self.assertRaises(TypeError):
			frappe.qb.get_query("QB Test Parent", ignore_permissions=True)

		with self.assertRaises(TypeError):
			frappe.qb.get_query("QB Test Parent", user="Administrator")

		from frappe.database.query import Permission

		q = frappe.qb.get_query("QB Test Parent", fields=["name"])
		Permission.check_permissions(q, user="Administrator")

		# Invalid column raises OperationalError
		with self.assertRaises(Exception):
			frappe.qb.get_query("QB Test Parent", fields=["non_existent_col"]).run(as_dict=True)
