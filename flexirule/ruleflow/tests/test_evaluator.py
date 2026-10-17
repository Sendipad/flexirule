# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

"""
Tests for ConditionEvaluator
"""

import unittest

import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.core.condition_operators import compare_values
from flexirule.ruleflow.core.evaluator import ConditionEvaluator


class TestConditionEvaluator(FrappeTestCase):
	"""Test cases for ConditionEvaluator"""

	def setUp(self):
		super().setUp()
		self.test_doc = frappe._dict(
			{
				"doctype": "ToDo",
				"status": "Open",
				"priority": "High",
				"description": "Test description",
				"date": "2023-01-01",
				"allocated_to": "Administrator",
			}
		)

	def test_shared_comparator_distinguishes_null_empty_and_falsy_values(self):
		self.assertFalse(compare_values(None, "==", ""))
		self.assertTrue(compare_values(None, "is_not_set"))
		self.assertTrue(compare_values("", "is_not_set"))
		self.assertFalse(compare_values(" ", "is_not_set"))
		self.assertTrue(compare_values(" ", "is_empty"))
		self.assertTrue(compare_values(0, "is_set"))
		self.assertTrue(compare_values(False, "is_set"))
		self.assertFalse(compare_values(0, "is_empty"))
		self.assertFalse(compare_values(False, "is_empty"))

	def test_shared_comparator_membership_and_contains_semantics(self):
		self.assertFalse(compare_values("Open", "in", []))
		self.assertTrue(compare_values("Open", "not_in", []))
		self.assertTrue(compare_values(0, "contains", "0"))
		self.assertTrue(compare_values(None, "not_contains", "x"))
		with self.assertRaises(TypeError):
			compare_values("Open", "in", None)

	def test_shared_comparator_length_uses_engine_length_contract(self):
		self.assertTrue(compare_values("  open  ", "length_eq", 4))
		self.assertTrue(compare_values([], "length_eq", 0))

	def test_evaluator_resolves_structured_static_flex_value(self):
		conditions_json = (
			'[{"left": {"ref": "doc.status"}, "op": "==", '
			'"right": {"value": {"mode": "static", "value": "Open"}}}]'
		)
		self.assertTrue(ConditionEvaluator(conditions_json).evaluate(self.test_doc))

	def test_document_reference_uses_field_resolver_for_nested_paths(self):
		from unittest.mock import MagicMock, patch

		condition = [{"left": {"ref": "doc.linked_doc.status"}, "op": "==", "right": {"value": "Open"}}]
		source_meta = MagicMock()
		source_meta.name = "ToDo"
		source_meta.istable = False
		source_meta.get_field.return_value = frappe._dict({"fieldtype": "Link", "options": "Customer"})
		target_meta = MagicMock()
		target_meta.name = "Customer"
		target_meta.istable = False
		target_meta.get_field.return_value = frappe._dict({"fieldtype": "Data"})
		with (
			patch("frappe.get_meta", side_effect=lambda name: source_meta if name == "ToDo" else target_meta),
			patch(
				"flexirule.ruleflow.utils.field_resolver.FieldResolver.resolve",
				return_value="Open",
			) as resolve,
		):
			self.assertTrue(ConditionEvaluator(condition, strict=True).evaluate(self.test_doc))
		resolve.assert_called_once_with(self.test_doc, "linked_doc.status")

	def test_strict_evaluator_rejects_unknown_doc_field(self):
		condition = [
			{
				"left": {"ref": "doc.no_such_condition_field"},
				"op": "==",
				"right": {"value": None},
			}
		]
		with self.assertRaises(frappe.ValidationError):
			ConditionEvaluator(condition, strict=True).evaluate(self.test_doc)

	def test_strict_evaluator_resolves_ctx_scope_from_runtime_context(self):
		condition = [
			{
				"left": {"ref": "ctx.current_value"},
				"op": "==",
				"right": {"value": "Open"},
			}
		]
		self.assertTrue(
			ConditionEvaluator(condition, strict=True).evaluate(
				self.test_doc,
				context={"ctx": {"current_value": "Open"}},
			)
		)

	def test_strict_evaluator_resolves_loop_scope_from_runtime_context(self):
		condition = [
			{
				"left": {"ref": "loop.current_value"},
				"op": "==",
				"right": {"value": "Open"},
			}
		]
		self.assertTrue(
			ConditionEvaluator(condition, strict=True).evaluate(
				self.test_doc,
				context={"loop": {"current_value": "Open"}},
			)
		)

	def test_strict_evaluator_resolves_flexvalue_variable_from_context(self):
		condition = [
			{
				"left": {"ref": "doc.priority"},
				"op": "==",
				"right": {"value": {"mode": "variable", "path": "vars.expected_priority"}},
			}
		]
		self.assertTrue(
			ConditionEvaluator(condition, strict=True).evaluate(
				self.test_doc,
				context={"vars": {"expected_priority": "High"}},
			)
		)

	def test_strict_evaluator_binds_collection_alias_in_shared_context(self):
		from unittest.mock import MagicMock, patch

		doc = frappe._dict(
			{
				"doctype": "ToDo",
				"items": [frappe._dict({"qty": 2}), frappe._dict({"qty": 8})],
			}
		)
		condition = {
			"op": "any",
			"collection": "doc.items",
			"alias": "line",
			"where": {
				"left": {"ref": "line.qty"},
				"op": ">",
				"right": {"value": {"mode": "variable", "path": "vars.minimum"}},
			},
		}
		source_meta = MagicMock()
		source_meta.name = "ToDo"
		source_meta.istable = False
		source_meta.get_field.side_effect = lambda fieldname: (
			frappe._dict({"fieldtype": "Table", "options": "ToDo Item"})
			if fieldname == "items"
			else None
		)
		row_meta = MagicMock()
		row_meta.name = "ToDo Item"
		row_meta.istable = True
		row_meta.get_field.return_value = frappe._dict({"fieldtype": "Int"})
		with patch(
			"frappe.get_meta",
			side_effect=lambda doctype: source_meta if doctype == "ToDo" else row_meta,
		):
			self.assertTrue(
				ConditionEvaluator(condition, strict=True).evaluate(
					doc,
					context={"vars": {"minimum": 5}},
				)
			)
	def test_strict_evaluator_uses_frappe_metadata_api_for_has_field(self):
		condition = [
			{
				"left": {"ref": "rule.document_type"},
				"op": "has_field",
				"right": {"value": "description"},
			}
		]
		self.assertTrue(
			ConditionEvaluator(condition, strict=True).evaluate(
				self.test_doc,
				context={"rule": {"document_type": "ToDo"}, "doctype": "ToDo"},
			)
		)

	def test_strict_evaluator_throws_frappe_validation_error_for_unknown_operator(self):
		condition = [{"left": {"ref": "doc.status"}, "op": "invented_operator", "right": {"value": "Open"}}]
		with self.assertRaises(frappe.ValidationError):
			ConditionEvaluator(condition, strict=True).evaluate(self.test_doc)

	def test_evaluate_simple_condition_true(self):
		"""Test evaluating a simple condition that returns True"""
		conditions_json = '[{"left": {"ref": "doc.status"}, "op": "==", "right": {"value": "Open"}}]'
		evaluator = ConditionEvaluator(conditions_json)

		result = evaluator.evaluate(self.test_doc)
		self.assertTrue(result)

	def test_evaluate_simple_condition_false(self):
		"""Test evaluating a simple condition that returns False"""
		conditions_json = '[{"left": {"ref": "doc.status"}, "op": "==", "right": {"value": "Closed"}}]'
		evaluator = ConditionEvaluator(conditions_json)

		result = evaluator.evaluate(self.test_doc)
		self.assertFalse(result)

	def test_evaluate_and_group_true(self):
		"""Test evaluating an AND group that returns True"""
		conditions_json = """[
            {"left": {"ref": "doc.status"}, "op": "==", "right": {"value": "Open"}},
            {"left": {"ref": "doc.priority"}, "op": "==", "right": {"value": "High"}}
        ]"""
		evaluator = ConditionEvaluator(conditions_json)

		result = evaluator.evaluate(self.test_doc)
		self.assertTrue(result)

	def test_evaluate_and_group_false(self):
		"""Test evaluating an AND group that returns False"""
		conditions_json = """[
            {"left": {"ref": "doc.status"}, "op": "==", "right": {"value": "Open"}},
            {"left": {"ref": "doc.priority"}, "op": "==", "right": {"value": "Low"}}
        ]"""
		evaluator = ConditionEvaluator(conditions_json)

		result = evaluator.evaluate(self.test_doc)
		self.assertFalse(result)

	def test_evaluate_or_group_true(self):
		"""Test evaluating an OR group that returns True"""
		conditions_json = """[
            {"left": {"ref": "doc.status"}, "op": "==", "right": {"value": "Closed"}, "logical_operator": "OR"},
            {"left": {"ref": "doc.priority"}, "op": "==", "right": {"value": "High"}}
        ]"""
		evaluator = ConditionEvaluator(conditions_json)

		result = evaluator.evaluate(self.test_doc)
		self.assertTrue(result)

	def test_evaluate_or_group_false(self):
		"""Test evaluating an OR group that returns False"""
		conditions_json = """[
            {"left": {"ref": "doc.status"}, "op": "==", "right": {"value": "Closed"}, "logical_operator": "OR"},
            {"left": {"ref": "doc.priority"}, "op": "==", "right": {"value": "Low"}}
        ]"""
		evaluator = ConditionEvaluator(conditions_json)

		result = evaluator.evaluate(self.test_doc)
		self.assertFalse(result)

	def test_evaluate_in_condition_true(self):
		"""Test evaluating an 'in' condition that returns True"""
		conditions_json = (
			'[{"left": {"ref": "doc.status"}, "op": "in", "right": {"value": ["Open", "Closed"]}}]'
		)
		evaluator = ConditionEvaluator(conditions_json)

		result = evaluator.evaluate(self.test_doc)
		self.assertTrue(result)

	def test_evaluate_not_in_condition_false(self):
		"""Test evaluating a 'not_in' condition that returns False"""
		conditions_json = (
			'[{"left": {"ref": "doc.status"}, "op": "not_in", "right": {"value": ["Open", "Closed"]}}]'
		)
		evaluator = ConditionEvaluator(conditions_json)

		result = evaluator.evaluate(self.test_doc)
		self.assertFalse(result)

	def test_evaluate_contains_condition_true(self):
		"""Test evaluating a 'contains' condition that returns True"""
		conditions_json = (
			'[{"left": {"ref": "doc.description"}, "op": "contains", "right": {"value": "description"}}]'
		)
		evaluator = ConditionEvaluator(conditions_json)

		result = evaluator.evaluate(self.test_doc)
		self.assertTrue(result)

	def test_evaluate_is_set_condition_true(self):
		"""Test evaluating an 'is_set' condition that returns True"""
		conditions_json = '[{"left": {"ref": "doc.status"}, "op": "is_set"}]'
		evaluator = ConditionEvaluator(conditions_json)

		result = evaluator.evaluate(self.test_doc)
		self.assertTrue(result)

	def test_evaluate_is_not_set_condition_false(self):
		"""Test evaluating an 'is_not_set' condition that returns False"""
		conditions_json = '[{"left": {"ref": "doc.status"}, "op": "is_not_set"}]'
		evaluator = ConditionEvaluator(conditions_json)

		result = evaluator.evaluate(self.test_doc)
		self.assertFalse(result)

	def test_evaluate_regex_condition_true(self):
		"""Test evaluating a 'regex' condition that returns True"""
		conditions_json = (
			'[{"left": {"ref": "doc.description"}, "op": "regex", "right": {"value": "^Test.*on$"}}]'
		)
		evaluator = ConditionEvaluator(conditions_json)

		result = evaluator.evaluate(self.test_doc)
		self.assertTrue(result)

	def test_evaluate_with_old_doc(self):
		"""Test resolving value from old_doc"""
		# Create a document with old_doc simulation
		doc = frappe.get_doc({"doctype": "ToDo", "description": "Original"})
		doc._doc_before_save = frappe._dict({"description": "Original"})
		doc.description = "Updated"

		conditions_json = (
			'[{"left": {"ref": "old_doc.description"}, "op": "==", "right": {"value": "Original"}}]'
		)
		evaluator = ConditionEvaluator(conditions_json)

		result = evaluator.evaluate(doc)
		self.assertTrue(result)

	def test_evaluate_with_row_context(self):
		"""Test resolving value from row context"""
		row = frappe._dict({"item_code": "ITM001", "qty": 10})
		conditions_json = (
			'[{"left": {"ref": "row.item_code"}, "op": "==", "right": {"value": "ITM001"}},'
			' {"left": {"ref": "row.qty"}, "op": ">", "right": {"value": 5}}]'
		)
		evaluator = ConditionEvaluator(conditions_json)

		# Passes both doc and row
		result = evaluator.evaluate(self.test_doc, row)
		self.assertTrue(result)

	def test_evaluate_with_dynamic_alias(self):
		"""Test resolving value using dynamic alias (if row is provided)"""
		row = frappe._dict({"status": "RowStatus"})
		# "item.status" should resolve to row.status if row is provided and we consider "item" an alias
		conditions_json = '[{"left": {"ref": "item.status"}, "op": "==", "right": {"value": "RowStatus"}}]'
		evaluator = ConditionEvaluator(conditions_json)

		result = evaluator.evaluate(self.test_doc, row)
		self.assertTrue(result)

	def test_evaluate_nested_conditions(self):
		"""Test evaluating nested conditions"""
		conditions_json = """[
            {
                "op": "OR",
                "conditions": [
                    {"left": {"ref": "doc.status"}, "op": "==", "right": {"value": "Closed"}},
                    {"left": {"ref": "doc.priority"}, "op": "==", "right": {"value": "High"}}
                ],
                "logical_operator": "OR"
            },
            {"left": {"ref": "doc.description"}, "op": "contains", "right": {"value": "Test"}}
        ]"""
		evaluator = ConditionEvaluator(conditions_json)

		result = evaluator.evaluate(self.test_doc)
		self.assertTrue(result)

	def test_evaluate_collection_any(self):
		"""Test evaluate_collection with 'any' logic"""
		doc = frappe.get_doc(
			{
				"doctype": "ToDo",
				"description": "Parent",
				# We'll mock the collection resolution since ToDo doesn't have child tables
			}
		)
		# Mocking items collection on the doc
		doc.items = [
			frappe._dict({"status": "Open", "amount": 100}),
			frappe._dict({"status": "Closed", "amount": 200}),
		]

		conditions_json = """[
            {
                "op": "any",
                "collection": "items",
                "where": {
                    "conditions": [
                        {"left": {"ref": "row.status"}, "op": "==", "right": {"value": "Closed"}}
                    ]
                }
            }
        ]"""
		evaluator = ConditionEvaluator(conditions_json)
		result = evaluator.evaluate(doc)
		self.assertTrue(result)

	def test_evaluate_collection_all(self):
		"""Test evaluate_collection with 'all' logic"""
		doc = frappe._dict(
			{
				"items": [
					frappe._dict({"qty": 10}),
					frappe._dict({"qty": 20}),
					frappe._dict({"qty": 30}),
				]
			}
		)

		conditions_json = """[
            {
                "op": "all",
                "collection": "items",
                "where": {
                    "conditions": [
                        {"left": {"ref": "row.qty"}, "op": ">", "right": {"value": 5}}
                    ]
                }
            }
        ]"""
		evaluator = ConditionEvaluator(conditions_json)
		result = evaluator.evaluate(doc)
		self.assertTrue(result)

	def test_evaluate_collection_none(self):
		"""Test evaluate_collection with 'none' logic"""
		doc = frappe._dict(
			{
				"items": [
					frappe._dict({"status": "Open"}),
					frappe._dict({"status": "Open"}),
				]
			}
		)

		conditions_json = """[
            {
                "op": "none",
                "collection": "items",
                "where": {
                    "conditions": [
                        {"left": {"ref": "row.status"}, "op": "==", "right": {"value": "Closed"}}
                    ]
                }
            }
        ]"""
		evaluator = ConditionEvaluator(conditions_json)
		result = evaluator.evaluate(doc)
		self.assertTrue(result)

	def test_get_field_value_with_dot_notation(self):
		"""Test getting field value with dot notation (though ToDo doesn't have child tables by default)"""
		evaluator = ConditionEvaluator("[]")
		# Test with a field that exists on the doc object even if not saved
		result = evaluator._get_field_value(self.test_doc, "doctype")
		self.assertEqual(result, "ToDo")

	def test_strict_evaluator_validates_fixed_link_target_doctype(self):
		from unittest.mock import MagicMock, patch

		doc = frappe._dict({"doctype": "Link Condition Source", "linked_record": "CUST-001"})
		meta = MagicMock()
		meta.get_field.return_value = frappe._dict({"fieldtype": "Link", "options": "Customer"})
		condition = [
			{
				"left": {"ref": "doc.linked_record"},
				"op": "==",
				"right": {"value": ["Customer", "CUST-001"]},
			}
		]

		with patch("frappe.get_meta", return_value=meta):
			self.assertTrue(ConditionEvaluator(condition, strict=True).evaluate(doc))

	def test_strict_evaluator_rejects_mismatched_fixed_link_target_doctype(self):
		from unittest.mock import MagicMock, patch

		doc = frappe._dict({"doctype": "Link Condition Source", "linked_record": "CUST-001"})
		meta = MagicMock()
		meta.get_field.return_value = frappe._dict({"fieldtype": "Link", "options": "Customer"})
		condition = [
			{
				"left": {"ref": "doc.linked_record"},
				"op": "==",
				"right": {"value": ["Supplier", "CUST-001"]},
			}
		]

		with patch("frappe.get_meta", return_value=meta):
			with self.assertRaises(frappe.ValidationError):
				ConditionEvaluator(condition, strict=True).evaluate(doc)

	def test_strict_evaluator_compares_dynamic_link_target_per_record(self):
		from unittest.mock import MagicMock, patch

		doc = frappe._dict(
			{
				"doctype": "Dynamic Link Condition Source",
				"party_type": "Supplier",
				"party": "SUP-001",
			}
		)
		meta = MagicMock()
		meta.get_field.side_effect = lambda fieldname: (
			frappe._dict({"fieldtype": "Dynamic Link", "options": "party_type"})
			if fieldname == "party"
			else None
		)
		equals_condition = [
			{
				"left": {"ref": "doc.party"},
				"op": "==",
				"right": {"value": ["Customer", "SUP-001"]},
			}
		]
		not_equals_condition = [
			{
				"left": {"ref": "doc.party"},
				"op": "!=",
				"right": {"value": ["Customer", "SUP-001"]},
			}
		]

		with patch("frappe.get_meta", return_value=meta):
			self.assertFalse(ConditionEvaluator(equals_condition, strict=True).evaluate(doc))
			self.assertTrue(ConditionEvaluator(not_equals_condition, strict=True).evaluate(doc))

	def test_check_link_match_true(self):
		"""Test check_link_match helper function returning True"""
		from flexirule.ruleflow.core.evaluator import check_link_match

		# Test simple match
		self.assertTrue(check_link_match("User", ["DocType", "User"], "=="))

		# Test 'in' match
		self.assertTrue(check_link_match("User", ["DocType", ["Task", "User"]], "in"))

	def test_check_link_match_false(self):
		"""Test check_link_match helper function returning False"""
		from flexirule.ruleflow.core.evaluator import check_link_match

		# Test mismatch
		self.assertFalse(check_link_match("User", ["DocType", "Task"], "=="))

		# Test 'not in' mismatch
		self.assertFalse(check_link_match("User", ["DocType", ["Task", "User"]], "not in"))
