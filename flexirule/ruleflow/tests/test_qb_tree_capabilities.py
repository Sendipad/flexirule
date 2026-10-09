# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

import uuid
from typing import ClassVar

import frappe
from frappe.tests.utils import FrappeTestCase


class TestQBTreeCapabilities(FrappeTestCase):
	"""
	Empirical Test Suite: Tree DocType Hierarchy Operators
	in frappe.qb.get_query().
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
		dt = f"QB Tree Node {cls._run_id}"
		if frappe.db.exists("DocType", dt):
			raise RuntimeError(f"Unexpected pre-existing DocType: {dt}")

		frappe.get_doc(
			{
				"doctype": "DocType",
				"name": dt,
				"module": "RuleFlow",
				"custom": 1,
				"is_tree": 1,
				"nsm_parent_field": f"parent_qb_tree_node_{cls._run_id.lower()}",
				"fields": [
					{"fieldname": "tree_name", "fieldtype": "Data", "label": "Tree Name", "reqd": 1},
					{
						"fieldname": f"parent_qb_tree_node_{cls._run_id.lower()}",
						"fieldtype": "Link",
						"options": dt,
						"label": "Parent Tree Node",
					},
					{"fieldname": "old_parent", "fieldtype": "Data", "label": "Old Parent"},
					{"fieldname": "is_group", "fieldtype": "Check", "label": "Is Group"},
					{"fieldname": "status", "fieldtype": "Data", "label": "Status"},
					{"fieldname": "lft", "fieldtype": "Int", "label": "lft", "hidden": 1},
					{"fieldname": "rgt", "fieldtype": "Int", "label": "rgt", "hidden": 1},
				],
			}
		).insert(ignore_permissions=True)
		cls._created_doctypes.append(dt)
		cls.tree_doctype = dt

		frappe.db.commit()

	@classmethod
	def _setup_test_records(cls):
		parent_field = f"parent_qb_tree_node_{cls._run_id.lower()}"

		root_a = frappe.get_doc(
			{
				"doctype": cls.tree_doctype,
				"tree_name": "_TEST_Root A",
				"is_group": 1,
				"status": "Active",
			}
		).insert(ignore_permissions=True)
		cls._created_records.append((cls.tree_doctype, root_a.name))

		branch_a1 = frappe.get_doc(
			{
				"doctype": cls.tree_doctype,
				"tree_name": "_TEST_Branch A1",
				parent_field: root_a.name,
				"is_group": 1,
				"status": "Active",
			}
		).insert(ignore_permissions=True)
		cls._created_records.append((cls.tree_doctype, branch_a1.name))

		leaf_a1a = frappe.get_doc(
			{
				"doctype": cls.tree_doctype,
				"tree_name": "_TEST_Leaf A1a",
				parent_field: branch_a1.name,
				"is_group": 0,
				"status": "Active",
			}
		).insert(ignore_permissions=True)
		cls._created_records.append((cls.tree_doctype, leaf_a1a.name))

		leaf_a1b = frappe.get_doc(
			{
				"doctype": cls.tree_doctype,
				"tree_name": "_TEST_Leaf A1b",
				parent_field: branch_a1.name,
				"is_group": 0,
				"status": "Inactive",
			}
		).insert(ignore_permissions=True)
		cls._created_records.append((cls.tree_doctype, leaf_a1b.name))

		root_b = frappe.get_doc(
			{
				"doctype": cls.tree_doctype,
				"tree_name": "_TEST_Root B",
				"is_group": 1,
				"status": "Active",
			}
		).insert(ignore_permissions=True)
		cls._created_records.append((cls.tree_doctype, root_b.name))

		cls.root_a = root_a
		cls.branch_a1 = branch_a1
		cls.leaf_a1a = leaf_a1a
		cls.leaf_a1b = leaf_a1b
		cls.root_b = root_b

		frappe.db.commit()

	def test_01_descendants_of_operator(self):
		"""Test 'descendants of' returns all recursive descendants excluding queried node."""
		res = frappe.qb.get_query(
			self.tree_doctype,
			fields=["name", "tree_name"],
			filters=[["name", "descendants of", self.root_a.name]],
		).run(as_dict=True)

		names = {r["tree_name"] for r in res}
		self.assertEqual(names, {"_TEST_Branch A1", "_TEST_Leaf A1a", "_TEST_Leaf A1b"})
		self.assertNotIn("_TEST_Root A", names)
		self.assertNotIn("_TEST_Root B", names)

	def test_02_descendants_of_inclusive_operator(self):
		"""Test 'descendants of (inclusive)' includes queried node itself."""
		res = frappe.qb.get_query(
			self.tree_doctype,
			fields=["name", "tree_name"],
			filters=[["name", "descendants of (inclusive)", self.root_a.name]],
		).run(as_dict=True)

		names = {r["tree_name"] for r in res}
		self.assertEqual(names, {"_TEST_Root A", "_TEST_Branch A1", "_TEST_Leaf A1a", "_TEST_Leaf A1b"})

	def test_03_ancestors_of_operator(self):
		"""Test 'ancestors of' returns all recursive ancestors excluding queried node."""
		res = frappe.qb.get_query(
			self.tree_doctype,
			fields=["name", "tree_name"],
			filters=[["name", "ancestors of", self.leaf_a1a.name]],
		).run(as_dict=True)

		names = {r["tree_name"] for r in res}
		self.assertEqual(names, {"_TEST_Root A", "_TEST_Branch A1"})

	def test_04_nonexistent_node_tree_filter(self):
		"""Nonexistent node name in 'descendants of' returns empty list safely."""
		res = frappe.qb.get_query(
			self.tree_doctype,
			fields=["name"],
			filters=[["name", "descendants of", "NON_EXISTENT_NODE"]],
		).run(as_dict=True)

		self.assertEqual(len(res), 0)

	def test_05_tree_operator_combined_with_field_filters(self):
		"""Tree operator combined with field equality condition ('status' = 'Active')."""
		res = frappe.qb.get_query(
			self.tree_doctype,
			fields=["name", "tree_name"],
			filters=[
				["name", "descendants of", self.root_a.name],
				["status", "=", "Active"],
			],
		).run(as_dict=True)

		names = {r["tree_name"] for r in res}
		self.assertEqual(names, {"_TEST_Branch A1", "_TEST_Leaf A1a"})
		self.assertNotIn("_TEST_Leaf A1b", names)
