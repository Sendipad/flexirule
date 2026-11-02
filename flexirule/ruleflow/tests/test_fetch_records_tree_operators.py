# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

import uuid
from typing import ClassVar

import frappe
from frappe.database.operator_map import OPERATOR_MAP
from frappe.database.utils import NestedSetHierarchy
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.core.action_handlers.query_records import QueryRecordsHandler
from flexirule.ruleflow.tests.test_helpers import safe_cleanup_test_resources
from flexirule.ruleflow.utils.frappe_query_compat import execute_query


class TestFetchRecordsTreeOperators(FrappeTestCase):
	"""Database integration coverage for Fetch Records nested-set filters on Frappe 15 and 16."""

	_created_doctypes: ClassVar[list[str]] = []
	_created_records: ClassVar[list[tuple[str, str]]] = []
	tree_doctype: ClassVar[str] = ""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls._created_doctypes = []
		cls._created_records = []
		cls.addClassCleanup(cls._cleanup_resources)
		cls.tree_doctype = f"Fetch Tree Node {uuid.uuid4().hex[:8].upper()}"
		cls._setup_tree_doctype()
		cls._setup_tree_records()

	@classmethod
	def _cleanup_resources(cls):
		try:
			safe_cleanup_test_resources(doctypes=cls._created_doctypes, records=cls._created_records)
		finally:
			cls._created_records.clear()
			cls._created_doctypes.clear()

	@classmethod
	def _setup_tree_doctype(cls):
		if not frappe.db.exists("DocType", cls.tree_doctype):
			frappe.get_doc(
				{
					"doctype": "DocType",
					"name": cls.tree_doctype,
					"module": "RuleFlow",
					"custom": 1,
					"is_tree": 1,
					"nsm_parent_field": "parent_fetch_records_tree_test_node",
					"fields": [
						{"fieldname": "tree_label", "fieldtype": "Data", "label": "Tree Label", "reqd": 1},
						{
							"fieldname": "parent_fetch_records_tree_test_node",
							"fieldtype": "Link",
							"options": cls.tree_doctype,
							"label": "Parent Tree Node",
						},
						{"fieldname": "old_parent", "fieldtype": "Data", "label": "Old Parent"},
						{"fieldname": "is_group", "fieldtype": "Check", "label": "Is Group"},
						{"fieldname": "lft", "fieldtype": "Int", "label": "Left", "hidden": 1},
						{"fieldname": "rgt", "fieldtype": "Int", "label": "Right", "hidden": 1},
					],
				}
			).insert(ignore_permissions=True)
			cls._created_doctypes.append(cls.tree_doctype)
		# Commit required for dynamic DDL schema creation in Frappe so MariaDB table definitions
		# and DocType metadata are immediately visible across test query execution.
		frappe.db.commit()

	@classmethod
	def _setup_tree_records(cls):
		cls.root = frappe.get_doc({"doctype": cls.tree_doctype, "tree_label": "Root", "is_group": 1}).insert(
			ignore_permissions=True
		)
		cls._created_records.append((cls.tree_doctype, cls.root.name))

		cls.child_a = frappe.get_doc(
			{
				"doctype": cls.tree_doctype,
				"tree_label": "Child A",
				"parent_fetch_records_tree_test_node": cls.root.name,
				"is_group": 1,
			}
		).insert(ignore_permissions=True)
		cls._created_records.append((cls.tree_doctype, cls.child_a.name))

		cls.grandchild_a = frappe.get_doc(
			{
				"doctype": cls.tree_doctype,
				"tree_label": "Grandchild A",
				"parent_fetch_records_tree_test_node": cls.child_a.name,
				"is_group": 0,
			}
		).insert(ignore_permissions=True)
		cls._created_records.append((cls.tree_doctype, cls.grandchild_a.name))

		cls.child_b = frappe.get_doc(
			{
				"doctype": cls.tree_doctype,
				"tree_label": "Child B",
				"parent_fetch_records_tree_test_node": cls.root.name,
				"is_group": 0,
			}
		).insert(ignore_permissions=True)
		cls._created_records.append((cls.tree_doctype, cls.child_b.name))

		cls.other_root = frappe.get_doc(
			{"doctype": cls.tree_doctype, "tree_label": "Other Root", "is_group": 1}
		).insert(ignore_permissions=True)
		cls._created_records.append((cls.tree_doctype, cls.other_root.name))

	def test_fetch_records_operator_contract_matches_portable_frappe_query_builder_operators(self):
		handler = QueryRecordsHandler()
		allowed = handler._FETCH_RECORDS_OPERATORS
		native_portable_operators = {
			"=",
			"!=",
			">",
			">=",
			"<",
			"<=",
			"like",
			"not like",
			"in",
			"not in",
			"between",
			"is",
			"timespan",
		}
		flexirule_aliases = {"starts with", "ends with"}

		# These assertions run inside each installed-version CI job, comparing the
		# Fetch Records contract to the actual Frappe source imported by that runtime.
		self.assertTrue(native_portable_operators.issubset(OPERATOR_MAP))
		self.assertTrue(native_portable_operators.issubset(allowed))
		self.assertTrue(flexirule_aliases.issubset(allowed))
		self.assertTrue({op.casefold() for op in NestedSetHierarchy}.issubset(allowed))
		# These entries are either invalid or version/dialect-specific in the upstream
		# Query Builder, so they are deliberately not part of Fetch Records' portable contract.
		for invalid_operator in ("<>", "regex", "ilike", "previous", "next", "nested_set"):
			with self.subTest(operator=invalid_operator):
				self.assertNotIn(invalid_operator, allowed)
				errors = handler._validate_canonical_fetch_filter_tree(
					{
						"type": "leaf",
						"field": "tree_label",
						"operator": invalid_operator,
						"value": {"mode": "static", "value": "Root"},
					}
				)
				self.assertTrue(any("operator is not supported" in error for error in errors))

	def test_operator_contract_also_rejects_unsupported_legacy_filter_rows(self):
		handler = QueryRecordsHandler()
		for operator in ("<>", "regex", "ilike", "previous", "next"):
			with self.subTest(operator=operator):
				errors = handler._validate_resolved_fetch_filter_operators(
					[[self.tree_doctype, "tree_label", operator, "Root"]],
					self.tree_doctype,
				)
				self.assertTrue(any("is not supported by Fetch Records" in error for error in errors))

	def test_resolved_is_values_and_legacy_tree_targets_are_validated(self):
		handler = QueryRecordsHandler()
		is_errors = handler._validate_resolved_fetch_filter_operators(
			[[self.tree_doctype, "tree_label", "is", "empty"]],
			self.tree_doctype,
		)
		self.assertTrue(any("must be 'set' or 'not set'" in error for error in is_errors))

		tree_errors = handler._validate_resolved_fetch_filter_operators(
			[["ToDo", "name", "descendants of", "some-name"]],
			"ToDo",
		)
		self.assertTrue(any("requires a Tree DocType" in error for error in tree_errors))

		valid_errors = handler._validate_resolved_fetch_filter_operators(
			[[self.tree_doctype, "name", "descendants of", self.root.name]],
			self.tree_doctype,
		)
		self.assertEqual(valid_errors, [])

	def test_is_operator_requires_native_set_value(self):
		handler = QueryRecordsHandler()
		for value in ("set", "not set", "SET", "Not Set"):
			with self.subTest(value=value):
				errors = handler._validate_canonical_fetch_filter_tree(
					{
						"type": "leaf",
						"field": "tree_label",
						"operator": "is",
						"value": {"mode": "static", "value": value},
					}
				)
				self.assertEqual(errors, [])

		errors = handler._validate_canonical_fetch_filter_tree(
			{
				"type": "leaf",
				"field": "tree_label",
				"operator": "is",
				"value": {"mode": "static", "value": "empty"},
			}
		)
		self.assertTrue(any("must be 'set' or 'not set'" in error for error in errors))

	def test_nested_set_operators_require_tree_doctype_context(self):
		handler = QueryRecordsHandler()
		invalid = handler._validate_canonical_fetch_filter_tree(
			{
				"type": "leaf",
				"field": "name",
				"operator": "descendants of",
				"value": {"mode": "static", "value": "some-name"},
			},
			reference_doctype="ToDo",
		)
		self.assertTrue(any("requires a Tree DocType" in error for error in invalid))

		valid_tree_name = handler._validate_canonical_fetch_filter_tree(
			{
				"type": "leaf",
				"field": "name",
				"operator": "descendants of",
				"value": {"mode": "static", "value": self.root.name},
			},
			reference_doctype=self.tree_doctype,
		)
		self.assertEqual(valid_tree_name, [])

		valid_tree_link = handler._validate_canonical_fetch_filter_tree(
			{
				"type": "leaf",
				"field": "parent_fetch_records_tree_test_node",
				"operator": "ancestors of",
				"value": {"mode": "static", "value": self.child_a.name},
			},
			reference_doctype=self.tree_doctype,
		)
		self.assertEqual(valid_tree_link, [])

	def _run_filter(self, filters):
		rows = execute_query(
			self.tree_doctype,
			{"fields": ["name"], "filters": filters},
			ignore_permissions=True,
		)
		return {row["name"] for row in rows}

	def test_all_five_nested_set_operators_as_single_filters(self):
		cases = {
			"descendants of": (
				self.root.name,
				{self.child_a.name, self.grandchild_a.name, self.child_b.name},
			),
			"descendants of (inclusive)": (
				self.root.name,
				{self.root.name, self.child_a.name, self.grandchild_a.name, self.child_b.name},
			),
			"not descendants of": (
				self.root.name,
				{self.root.name, self.other_root.name},
			),
			"ancestors of": (
				self.grandchild_a.name,
				{self.root.name, self.child_a.name},
			),
			"not ancestors of": (
				self.grandchild_a.name,
				{self.grandchild_a.name, self.child_b.name, self.other_root.name},
			),
		}

		for operator, (target, expected_names) in cases.items():
			with self.subTest(operator=operator):
				# A one-leaf canonical tree can collapse to this bare leaf shape.
				actual_names = self._run_filter(["name", operator, target])
				self.assertEqual(actual_names, expected_names)

	def test_all_five_nested_set_operators_compose_with_and_and_or(self):
		cases = {
			"descendants of": (
				self.root.name,
				{self.child_a.name, self.grandchild_a.name, self.child_b.name},
				self.child_a.name,
				self.root.name,
			),
			"descendants of (inclusive)": (
				self.root.name,
				{self.root.name, self.child_a.name, self.grandchild_a.name, self.child_b.name},
				self.root.name,
				self.other_root.name,
			),
			"not descendants of": (
				self.root.name,
				{self.root.name, self.other_root.name},
				self.other_root.name,
				self.child_a.name,
			),
			"ancestors of": (
				self.grandchild_a.name,
				{self.root.name, self.child_a.name},
				self.root.name,
				self.child_b.name,
			),
			"not ancestors of": (
				self.grandchild_a.name,
				{self.grandchild_a.name, self.child_b.name, self.other_root.name},
				self.grandchild_a.name,
				self.root.name,
			),
		}

		for operator, (target, hierarchy_names, and_name, or_name) in cases.items():
			for connector in ("and", "or"):
				with self.subTest(operator=operator, connector=connector):
					other_name = and_name if connector == "and" else or_name
					filters = [
						["name", operator, target],
						connector,
						["name", "=", other_name],
					]
					actual_names = self._run_filter(filters)
					if connector == "and":
						self.assertEqual(actual_names, hierarchy_names & {and_name})
						self.assertTrue(actual_names, "AND case should retain a matching hierarchy node")
					else:
						self.assertEqual(actual_names, hierarchy_names | {or_name})
