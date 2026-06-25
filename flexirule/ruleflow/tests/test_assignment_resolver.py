import json
import unittest

import frappe

from flexirule.ruleflow.core.action_handlers.assignment import AssignmentHandler
from flexirule.ruleflow.core.value_resolver import ValueResolver


class TestAssignmentResolver(unittest.TestCase):
	def setUp(self):
		self.handler = AssignmentHandler()
		self.doc = frappe._dict(
			{
				"doctype": "User",
				"first_name": "John",
				"last_name": "Doe",
				"amount": 100,
				"creation": "2026-05-22 12:00:00",
				"items": [{"item_name": "A", "rate": 10}, {"item_name": "B", "rate": 20}],
			}
		)
		self.context = {"doc": self.doc, "vars": {}}
		self.engine = frappe._dict(
			{
				"_log": lambda *args: None,
				"rule": frappe._dict({"name": "Test Rule"}),
				"_evaluate_python_condition": lambda expr, ctx: True,
			}
		)

	def test_compile_resolver_mode(self):
		val = {
			"mode": "resolver",
			"config": {
				"kind": "math_formula",
				"field_a": "doc.amount",
				"math_op": "+",
				"field_b_type": "constant",
				"constant_b": 50,
				"precision": 2,
			},
		}
		resolver = ValueResolver.compile(val)
		result = resolver.resolve(self.context)
		self.assertEqual(result, 150.00)

	def test_compile_format_resolver(self):
		val = {
			"mode": "resolver",
			"config": {
				"kind": "format",
				"fmt_op": "format_date",
				"fmt_field": "doc.creation",
				"fmt_config": "yyyy-MM-dd",
			},
		}
		resolver = ValueResolver.compile(val)
		result = resolver.resolve(self.context)
		self.assertEqual(result, "2026-05-22")

	def test_compile_normalize_resolver(self):
		val = {
			"mode": "resolver",
			"config": {"kind": "normalization", "norm_op": "upper", "norm_field": "doc.first_name"},
		}
		resolver = ValueResolver.compile(val)
		result = resolver.resolve(self.context)
		self.assertEqual(result, "JOHN")

	def test_compile_variable_mode(self):
		val = {"mode": "variable", "path": "doc.last_name"}
		resolver = ValueResolver.compile(val)
		self.assertEqual(resolver.resolve(self.context), "Doe")

	def test_compile_expression_mode(self):
		val = {
			"mode": "expression",
			"value": [
				{"type": "text", "value": "Customer: "},
				{"type": "variableToken", "attrs": {"path": "doc.first_name"}},
				{"type": "text", "value": " "},
				{"type": "variableToken", "attrs": {"path": "doc.last_name"}},
			],
		}
		resolver = ValueResolver.compile(val)
		self.assertEqual(resolver.resolve(self.context), "Customer: John Doe")

	def test_math_formula_operations(self):
		ops = {
			"+": 150.0,
			"-": 50.0,
			"*": 5000.0,
			"/": 2.0,
		}
		for op, expected in ops.items():
			val = {
				"mode": "resolver",
				"config": {
					"kind": "math_formula",
					"field_a": "doc.amount",
					"math_op": op,
					"field_b_type": "constant",
					"constant_b": 50,
				},
			}
			resolver = ValueResolver.compile(val)
			self.assertEqual(resolver.resolve(self.context), expected)

	def test_math_formula_division_by_zero(self):
		val = {
			"mode": "resolver",
			"config": {
				"kind": "math_formula",
				"field_a": "doc.amount",
				"math_op": "/",
				"field_b_type": "constant",
				"constant_b": 0,
			},
		}
		resolver = ValueResolver.compile(val)
		self.assertEqual(resolver.resolve(self.context), 0.0)

	def test_math_formula_field_b(self):
		self.context["vars"]["multiplier"] = 2
		val = {
			"mode": "resolver",
			"config": {
				"kind": "math_formula",
				"field_a": "doc.amount",
				"math_op": "*",
				"field_b_type": "field",
				"field_b": "vars.multiplier",
			},
		}
		resolver = ValueResolver.compile(val)
		self.assertEqual(resolver.resolve(self.context), 200.0)

	def test_format_resolver_money(self):
		# Static currency
		val = {
			"mode": "resolver",
			"config": {
				"kind": "format",
				"fmt_op": "fmt_money",
				"fmt_field": "doc.amount",
				"fmt_config": "USD",
			},
		}
		resolver = ValueResolver.compile(val)
		result = resolver.resolve(self.context)
		# Just check if it's a non-empty string and contains 100
		self.assertIsInstance(result, str)
		self.assertIn("100", result)

		# Dynamic currency
		self.doc.update({"currency": "EUR"})
		if isinstance(val["config"], dict):
			val["config"]["fmt_config"] = "doc.currency"
		resolver = ValueResolver.compile(val)
		result = resolver.resolve(self.context)
		self.assertIn("100", result)

	def test_format_resolver_string(self):
		val = {
			"mode": "resolver",
			"config": {
				"kind": "format",
				"fmt_op": "format",
				"fmt_field": "doc.first_name",
				"fmt_config": "Hello, {}!",
			},
		}
		resolver = ValueResolver.compile(val)
		self.assertEqual(resolver.resolve(self.context), "Hello, John!")

	def test_normalization_legacy_ops(self):
		# Legacy ops mapping in NormalizationResolver
		# Note: title, upper, and lower do NOT trim by default in their underlying operations
		# whereas slug and snake_case do.
		ops = {
			"trim": "John Doe",
			"slug": "john-doe",
			"snake": "john_doe",
			"title": "  John Doe  ",
			"upper": "  JOHN DOE  ",
			"lower": "  john doe  ",
		}
		self.context["doc"]["raw_name"] = "  John Doe  "
		for op, expected in ops.items():
			val = {
				"mode": "resolver",
				"config": {"kind": "normalization", "norm_op": op, "norm_field": "doc.raw_name"},
			}
			resolver = ValueResolver.compile(val)
			result = resolver.resolve(self.context)
			self.assertEqual(result, expected, f"Failed for op: {op}")

	def test_variable_resolver_fallback(self):
		# Test fallback to doc
		val = {"mode": "variable", "path": "first_name"}
		resolver = ValueResolver.compile(val)
		self.assertEqual(resolver.resolve(self.context), "John")

		# Test fallback to vars
		self.context["vars"]["global_status"] = "Active"
		val = {"mode": "variable", "path": "global_status"}
		resolver = ValueResolver.compile(val)
		self.assertEqual(resolver.resolve(self.context), "Active")

		# Test missing
		val = {"mode": "variable", "path": "non_existent"}
		resolver = ValueResolver.compile(val)
		self.assertIsNone(resolver.resolve(self.context))
