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
