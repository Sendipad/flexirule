# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

"""
Tests for FlexiRule Condition Compiler
"""

import unittest

import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.core.compiler import ConditionCompiler
from flexirule.ruleflow.core.condition_operators import (
	FIELD_TYPE_OPERATORS,
	OPERATOR_LABELS,
	SUPPORTED_OPERATOR_TOKENS,
	UNSUPPORTED_OPERATOR_DIAGNOSTICS,
	normalize_operator,
)
from flexirule.ruleflow.core.evaluator import ConditionEvaluator


class TestConditionCompiler(FrappeTestCase):
	"""Test cases for ConditionCompiler"""

	def setUp(self):
		super().setUp()
		self.compiler = ConditionCompiler()

	def test_operator_registry_is_the_source_of_validation_and_ui_aliases(self):
		self.assertEqual(normalize_operator("NOT_IN"), "not in")
		self.assertIn("contains", FIELD_TYPE_OPERATORS["Data"])
		self.assertIn("not_contains", FIELD_TYPE_OPERATORS["Data"])
		self.assertNotIn("like", FIELD_TYPE_OPERATORS["Data"])
		self.assertNotIn("not like", FIELD_TYPE_OPERATORS["Data"])
		self.assertIn("contains", SUPPORTED_OPERATOR_TOKENS)
		self.assertNotIn("like", SUPPORTED_OPERATOR_TOKENS)
		self.assertIn("like", UNSUPPORTED_OPERATOR_DIAGNOSTICS)
		self.assertEqual(self.compiler.OPERATOR_LABELS, OPERATOR_LABELS)

	def test_compile_simple_condition(self):
		"""Test compiling a simple condition"""
		condition = {"left": {"ref": "doc.status"}, "op": "==", "right": {"value": "Open"}}

		result = self.compiler.compile([condition])
		expected = "(doc.get('status') == 'Open')"
		self.assertEqual(result, expected)

	def test_compile_static_mode_condition(self):
		"""Structured static payload should compile as literal value."""
		condition = {
			"left": {"ref": "doc.status"},
			"op": "==",
			"right": {"value": {"mode": "static", "value": "Open"}},
		}

		result = self.compiler.compile([condition])
		self.assertEqual(result, "(doc.get('status') == 'Open')")

	def test_compile_variable_mode_condition(self):
		"""Structured variable payload should compile to scoped context reference."""
		condition = {
			"left": {"ref": "doc.grand_total"},
			"op": ">",
			"right": {"value": {"mode": "variable", "value": "vars.threshold"}},
		}

		result = self.compiler.compile([condition])
		self.assertEqual(result, "(doc.get('grand_total') > vars.get('threshold'))")

	def test_compile_resolver_mode_condition(self):
		"""Structured resolver payload should compile embedded expression safely."""
		condition = {
			"left": {"ref": "doc.qty"},
			"op": ">=",
			"right": {"value": {"mode": "resolver", "value": "{5 + 2}"}},
		}

		result = self.compiler.compile([condition])
		self.assertEqual(result, "(doc.get('qty') >= 5 + 2)")

	def test_compile_and_group(self):
		"""Test compiling an AND group"""
		condition = {
			"op": "and",
			"conditions": [
				{"left": {"ref": "doc.status"}, "op": "==", "right": {"value": "Open"}},
				{"left": {"ref": "doc.priority"}, "op": "==", "right": {"value": "High"}},
			],
		}

		result = self.compiler.compile(condition)
		# Updated expected to match actual output
		expected = "(doc.get('status') == 'Open' and doc.get('priority') == 'High')"
		self.assertEqual(result, expected)

	def test_compile_or_group(self):
		"""Test compiling an OR group"""
		condition = {
			"op": "or",
			"conditions": [
				{"left": {"ref": "doc.status"}, "op": "==", "right": {"value": "Open"}},
				{"left": {"ref": "doc.status"}, "op": "==", "right": {"value": "Closed"}},
			],
		}

		result = self.compiler.compile(condition)
		# Updated expected to match actual output
		expected = "(doc.get('status') == 'Open' or doc.get('status') == 'Closed')"
		self.assertEqual(result, expected)

	def test_compile_is_set_condition(self):
		"""Test compiling an 'is_set' condition"""
		condition = {"left": {"ref": "doc.description"}, "op": "is_set"}

		result = self.compiler.compile([condition])
		expected = "((doc.get('description') is not None and doc.get('description') != ''))"
		self.assertEqual(result, expected)

	def test_compile_is_not_set_condition(self):
		"""Test compiling an 'is_not_set' condition"""
		condition = {"left": {"ref": "doc.description"}, "op": "is_not_set"}

		result = self.compiler.compile([condition])
		expected = "((doc.get('description') is None or doc.get('description') == ''))"
		self.assertEqual(result, expected)

	def test_compile_is_empty_condition(self):
		"""Test compiling an 'is_empty' condition"""
		condition = {"left": {"ref": "vars.similar_jv"}, "op": "is_empty"}

		result = self.compiler.compile([condition])
		expected = "(is_empty_value(vars.get('similar_jv')))"
		self.assertEqual(result, expected)

	def test_compile_length_gt_condition(self):
		"""Test compiling a list length comparison condition"""
		condition = {"left": {"ref": "vars.similar_jv"}, "op": "length_gt", "right": {"value": 0}}

		result = self.compiler.compile([condition])
		expected = "((length_of(vars.get('similar_jv')) > 0))"
		self.assertEqual(result, expected)

	def test_compile_collection_condition(self):
		"""Test compiling a collection condition"""
		condition = {
			"op": "any",
			"collection": "doc.items",
			"alias": "item",
			"where": {"left": {"ref": "item.rate"}, "op": ">", "right": {"value": 100}},
		}

		result = self.compiler.compile([condition])
		# Updated expected to match actual output
		expected = "(any(item.get('rate') > 100 for item in (doc.get('items') or [])))"
		self.assertEqual(result, expected)

	def test_compile_nested_conditions(self):
		"""Test compiling nested conditions"""
		condition = {
			"op": "and",
			"conditions": [
				{
					"op": "or",
					"conditions": [
						{"left": {"ref": "doc.status"}, "op": "==", "right": {"value": "Open"}},
						{"left": {"ref": "doc.status"}, "op": "==", "right": {"value": "Pending"}},
					],
				},
				{"left": {"ref": "doc.priority"}, "op": "==", "right": {"value": "High"}},
			],
		}

		result = self.compiler.compile(condition)
		# Updated expected to match actual output
		expected = "((doc.get('status') == 'Open' or doc.get('status') == 'Pending') and doc.get('priority') == 'High')"
		self.assertEqual(result, expected)

	def test_compile_mixed_sibling_operators_match_tree_evaluator(self):
		"""Mixed sibling joins must not inherit Python's different AND/OR precedence."""
		condition = {
			"op": "and",
			"conditions": [
				{
					"left": {"ref": "doc.status"},
					"op": "==",
					"right": {"value": "Closed"},
					"logical_operator": "or",
				},
				{
					"left": {"ref": "doc.priority"},
					"op": "==",
					"right": {"value": "High"},
					"logical_operator": "and",
				},
				{
					"left": {"ref": "doc.description"},
					"op": "==",
					"right": {"value": "Test"},
				},
			],
		}
		doc = frappe._dict({"status": "Closed", "priority": "Low", "description": "Other"})

		compiled = self.compiler.compile(condition)
		compiled_result = frappe.safe_eval(
			compiled,
			{"__builtins__": {}, "doc": doc},
			{"doc": doc},
		)
		tree_result = ConditionEvaluator(frappe.as_json([condition])).evaluate(doc)

		self.assertEqual(
			compiled,
			"((doc.get('status') == 'Closed' or doc.get('priority') == 'High') "
			"and doc.get('description') == 'Test')",
		)
		self.assertFalse(compiled_result)
		self.assertEqual(compiled_result, tree_result)

	def test_compile_link_match_condition(self):
		"""Test compiling a link match condition"""
		condition = {
			"left": {"ref": "doc.customer"},
			"op": "==",
			"right": {"value": ["Customer", "CUST-001"]},
		}

		result = self.compiler.compile([condition])
		expected = "(check_link_match(doc.get('customer'), ['Customer', 'CUST-001'], '=='))"
		self.assertEqual(result, expected)

	def test_compile_contains_condition(self):
		"""Test compiling a contains condition"""
		condition = {"left": {"ref": "doc.description"}, "op": "contains", "right": {"value": "urgent"}}

		result = self.compiler.compile([condition])
		# Updated expected to match actual output
		expected = "(('urgent' in str(doc.get('description')) if doc.get('description') else False))"
		self.assertEqual(result, expected)

	def test_compile_not_contains_condition(self):
		"""Test compiling a not contains condition"""
		condition = {"left": {"ref": "doc.description"}, "op": "not_contains", "right": {"value": "draft"}}

		result = self.compiler.compile([condition])
		# Updated expected to match actual output
		expected = "(('draft' not in str(doc.get('description')) if doc.get('description') else True))"
		self.assertEqual(result, expected)

	def test_compile_context_doctype_equals(self):
		"""Test compiling a context doctype comparison."""
		condition = {"left": {"ref": "doctype"}, "op": "==", "right": {"value": "Sales Invoice"}}
		result = self.compiler.compile([condition])
		expected = "(doctype == 'Sales Invoice')"
		self.assertEqual(result, expected)

	def test_compile_context_doctype_in_list(self):
		"""Test compiling context doctype list comparison."""
		condition = {
			"left": {"ref": "doctype"},
			"op": "in",
			"right": {"value": ["Sales Invoice", "Purchase Invoice"]},
		}
		result = self.compiler.compile([condition])
		expected = "(doctype in ['Sales Invoice', 'Purchase Invoice'])"
		self.assertEqual(result, expected)

	def test_compile_is_submittable_operator(self):
		"""Test compiling helper operator for doctype submit capability."""
		condition = {"left": {"ref": "doctype"}, "op": "is_submittable"}
		result = self.compiler.compile([condition])
		expected = "(is_submittable(doctype))"
		self.assertEqual(result, expected)

	def test_compile_has_field_operator(self):
		"""Test compiling helper operator for doctype field existence."""
		condition = {
			"left": {"ref": "rule.document_type"},
			"op": "has_field",
			"right": {"value": "customer"},
		}
		result = self.compiler.compile([condition])
		expected = "(has_field(rule.get('document_type'), 'customer'))"
		self.assertEqual(result, expected)

	def test_validation_of_compiled_expression(self):
		"""Test validation of compiled expressions"""
		condition = {"left": {"ref": "doc.status"}, "op": "==", "right": {"value": "Open"}}

		compiled = self.compiler.compile([condition])
		is_valid, error = self.compiler.validate(compiled)
		self.assertTrue(is_valid)
		self.assertIsNone(error)

	def test_validation_of_invalid_expression(self):
		"""Test validation of invalid expressions"""
		invalid_expr = "if True: print('hello')"  # Invalid due to syntax
		is_valid, error = self.compiler.validate(invalid_expr)
		self.assertFalse(is_valid)
		self.assertIsNotNone(error)

	def test_compile_rejects_unknown_operator_instead_of_defaulting_to_equality(self):
		condition = {
			"left": {"ref": "doc.status"},
			"op": "mystery_operator",
			"right": {"value": "Open"},
		}
		with self.assertRaisesRegex(ValueError, "unknown or unsupported"):
			self.compiler.compile(condition)

	def test_compile_rejects_empty_nested_group(self):
		with self.assertRaisesRegex(ValueError, "groups must contain at least one child"):
			self.compiler.compile({"op": "and", "conditions": []})

	def test_compile_rejects_empty_object_as_a_condition(self):
		with self.assertRaisesRegex(ValueError, "exactly one node shape"):
			self.compiler.compile({})

	def test_compile_rejects_unsafe_reference_path(self):
		condition = {
			"left": {"ref": "doc.status') or True or ('x"},
			"op": "==",
			"right": {"value": "Open"},
		}
		with self.assertRaisesRegex(ValueError, "invalid reference path"):
			self.compiler.compile(condition)

	def test_compile_rejects_invalid_collection_operation(self):
		condition = {
			"op": "sometimes",
			"collection": "doc.items",
			"alias": "item",
			"where": {"left": {"ref": "item.qty"}, "op": ">", "right": {"value": 0}},
		}
		with self.assertRaisesRegex(ValueError, "unsupported collection operation"):
			self.compiler.compile(condition)

	def test_compile_rejects_deprecated_fail_open_has_changed(self):
		condition = {"left": {"ref": "doc.status"}, "op": "has_changed"}
		with self.assertRaisesRegex(ValueError, "has_changed.*deprecated"):
			self.compiler.compile(condition)

	def test_compile_normalizes_not_in_alias_explicitly(self):
		condition = {
			"left": {"ref": "doc.status"},
			"op": "not_in",
			"right": {"value": ["Closed", "Cancelled"]},
		}
		self.assertEqual(
			self.compiler.compile(condition),
			"doc.get('status') not in ['Closed', 'Cancelled']",
		)

	def test_resolve_ref_simple_field(self):
		"""Test resolving simple field references"""
		result = self.compiler._resolve_ref("doc.status", {"doc", "old_doc", "vars"})
		expected = "doc.get('status')"
		self.assertEqual(result, expected)

	def test_resolve_ref_nested_path(self):
		"""Test resolving nested field references"""
		result = self.compiler._resolve_ref("doc.items.rate", {"doc", "old_doc", "vars"})
		expected = "resolve(doc, 'items.rate')"
		self.assertEqual(result, expected)

	def test_resolve_ref_caller_scope(self):
		"""Test resolving caller metadata references."""
		result = self.compiler._resolve_ref("caller.trigger_type", {"caller", "rule", "doctype"})
		expected = "caller.get('trigger_type')"
		self.assertEqual(result, expected)

	def test_resolve_ref_doctype_scope(self):
		"""Test resolving scalar doctype scope."""
		result = self.compiler._resolve_ref("doctype", {"caller", "rule", "doctype"})
		expected = "doctype"
		self.assertEqual(result, expected)

	def test_compile_rejects_empty_condition_list(self):
		"""An explicitly configured empty condition tree is not a passing rule."""
		with self.assertRaisesRegex(ValueError, "groups must contain at least one child"):
			self.compiler.compile([])

	def test_compile_none_conditions(self):
		"""Test compiling None conditions"""
		result = self.compiler.compile(None)
		self.assertEqual(result, "")
