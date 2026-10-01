# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

import copy
import unittest
from typing import Any

import frappe

from flexirule.ruleflow.core.action_handlers.query_records import (
	QueryRecordsHandler,
	reconcile_query_doc_action,
)


class TestQueryDocSync(unittest.TestCase):
	def setUp(self):
		self.handler = QueryRecordsHandler()

	def test_1_reference_doctype_updates_config_doctype_name(self):
		"""1. Changing reference_doctype updates config.doctype_name."""
		action = frappe._dict(
			{
				"action_type": "Query Records",
				"operation": "Query Doc",
				"reference_doctype": "Journal Entry",
				"config": {"fetch_strategy": "Get doc"},
			}
		)
		reconcile_query_doc_action(action)
		self.assertEqual(action.config.get("doctype_name"), "Journal Entry")

	def test_2_reference_docname_updates_config_docname(self):
		"""2. Changing reference_docname updates config.docname."""
		action = frappe._dict(
			{
				"action_type": "Query Records",
				"operation": "Query Doc",
				"reference_docname": "ACC-JV-2026-00001",
				"config": {"doctype_name": "Journal Entry"},
			}
		)
		reconcile_query_doc_action(action)
		self.assertEqual(action.config.get("docname"), "ACC-JV-2026-00001")

	def test_3_config_doctype_name_updates_reference_doctype(self):
		"""3. Changing config.doctype_name updates reference_doctype."""
		action = frappe._dict(
			{
				"action_type": "Query Records",
				"operation": "Query Doc",
				"reference_doctype": None,
				"config": {"doctype_name": "Sales Invoice"},
			}
		)
		reconcile_query_doc_action(action)
		self.assertEqual(action.reference_doctype, "Sales Invoice")

	def test_4_config_docname_updates_reference_docname(self):
		"""4. Changing config.docname updates reference_docname."""
		action = frappe._dict(
			{
				"action_type": "Query Records",
				"operation": "Query Doc",
				"reference_docname": None,
				"config": {"doctype_name": "Sales Invoice", "docname": "SINV-00042"},
			}
		)
		reconcile_query_doc_action(action)
		self.assertEqual(action.reference_docname, "SINV-00042")

	def test_5_initial_load_only_rule_action_populated(self):
		"""5. Initial loading with only Rule Action fields populated synchronizes Query Doc config."""
		action = frappe._dict(
			{
				"action_type": "Query Records",
				"operation": "Query Doc",
				"reference_doctype": "Journal Entry",
				"reference_docname": "ACC-JV-2026-00668",
				"config": {},
			}
		)
		reconcile_query_doc_action(action)
		self.assertEqual(action.config.get("doctype_name"), "Journal Entry")
		self.assertEqual(action.config.get("docname"), "ACC-JV-2026-00668")

	def test_6_initial_load_only_query_doc_config_populated(self):
		"""6. Initial loading with only Query Doc config populated synchronizes Rule Action fields."""
		action = frappe._dict(
			{
				"action_type": "Query Records",
				"operation": "Query Doc",
				"reference_doctype": None,
				"reference_docname": None,
				"config": {"doctype_name": "Sales Invoice", "docname": "SINV-00042"},
			}
		)
		reconcile_query_doc_action(action)
		self.assertEqual(action.reference_doctype, "Sales Invoice")
		self.assertEqual(action.reference_docname, "SINV-00042")

	def test_7_existing_matching_values_remain_stable(self):
		"""7. Existing matching values remain stable."""
		action = frappe._dict(
			{
				"action_type": "Query Records",
				"operation": "Query Doc",
				"reference_doctype": "Journal Entry",
				"reference_docname": "ACC-JV-2026-00668",
				"config": {"doctype_name": "Journal Entry", "docname": "ACC-JV-2026-00668"},
			}
		)
		original_config = copy.deepcopy(action.config)
		reconcile_query_doc_action(action)
		self.assertEqual(action.reference_doctype, "Journal Entry")
		self.assertEqual(action.reference_docname, "ACC-JV-2026-00668")
		self.assertEqual(action.config, original_config)

	def test_8_conflicting_initial_values_rule_action_precedence(self):
		"""8. Conflicting initial values follow deterministic precedence (reference_* wins)."""
		action = frappe._dict(
			{
				"action_type": "Query Records",
				"operation": "Query Doc",
				"reference_doctype": "Journal Entry",
				"reference_docname": "ACC-JV-001",
				"config": {"doctype_name": "Sales Invoice", "docname": "ACC-JV-002"},
			}
		)
		reconcile_query_doc_action(action)
		self.assertEqual(action.reference_doctype, "Journal Entry")
		self.assertEqual(action.reference_docname, "ACC-JV-001")
		self.assertEqual(action.config.get("doctype_name"), "Journal Entry")
		self.assertEqual(action.config.get("docname"), "ACC-JV-001")

	def test_9_no_recursive_update_loops(self):
		"""9. Synchronization does not create recursive update loops or instability on repeated calls."""
		action = frappe._dict(
			{
				"action_type": "Query Records",
				"operation": "Query Doc",
				"reference_doctype": "Journal Entry",
				"reference_docname": "ACC-JV-001",
				"config": {"doctype_name": "Journal Entry", "docname": "ACC-JV-001"},
			}
		)
		for _ in range(10):
			reconcile_query_doc_action(action)
		self.assertEqual(action.reference_doctype, "Journal Entry")
		self.assertEqual(action.reference_docname, "ACC-JV-001")
		self.assertEqual(action.config.get("doctype_name"), "Journal Entry")
		self.assertEqual(action.config.get("docname"), "ACC-JV-001")

	def test_10_flexvalue_complex_structures_preserved(self):
		"""10. Dynamic/value-resolver configurations (dict structures) are preserved correctly."""
		flex_val_dt = {"mode": "expression", "value": "doc.target_doctype"}
		flex_val_dn = {"mode": "expression", "value": "doc.target_docname"}
		action = frappe._dict(
			{
				"action_type": "Query Records",
				"operation": "Query Doc",
				"reference_doctype": flex_val_dt,
				"reference_docname": flex_val_dn,
				"config": {},
			}
		)
		reconcile_query_doc_action(action)
		self.assertIsInstance(action.config.get("doctype_name"), dict)
		self.assertEqual(action.config.get("doctype_name"), flex_val_dt)
		self.assertIsInstance(action.config.get("docname"), dict)
		self.assertEqual(action.config.get("docname"), flex_val_dn)

	def test_11_query_doc_runtime_behavior_unchanged(self):
		"""11. Query Doc runtime behavior remains unchanged."""
		todo = frappe.get_doc(
			{
				"doctype": "ToDo",
				"description": "Runtime Behavior Test Task",
			}
		).insert(ignore_permissions=True)

		action = frappe._dict(
			{
				"action_type": "Query Records",
				"operation": "Query Doc",
				"reference_doctype": "ToDo",
				"reference_docname": todo.name,
				"config": {"fetch_strategy": "Get doc"},
			}
		)

		context: dict[str, Any] = {}
		result, _ = self.handler.execute(action, context, None)
		self.assertIsNotNone(result)
		self.assertEqual(result.get("doctype"), "ToDo")
		self.assertEqual(result.get("name"), todo.name)
		self.assertEqual(result.get("description"), "Runtime Behavior Test Task")
