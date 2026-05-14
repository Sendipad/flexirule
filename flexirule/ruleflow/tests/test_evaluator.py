# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

"""
Tests for ConditionEvaluator
"""

import unittest

import frappe
from frappe.tests.utils import FrappeTestCase

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
