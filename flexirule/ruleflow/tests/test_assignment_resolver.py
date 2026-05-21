import json
import unittest

import frappe

from flexirule.ruleflow.core.action_handlers.assignment import AssignmentHandler


class TestAssignmentResolver(unittest.TestCase):
	def setUp(self):
		self.handler = AssignmentHandler()
		self.doc = frappe._dict(
			{
				"doctype": "User",
				"first_name": "John",
				"last_name": "Doe",
				"amount": 100,
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
				"field_a": "amount",
				"math_op": "+",
				"field_b_type": "constant",
				"constant_b": 50,
				"precision": 2,
			},
			"expression": "{frappe.utils.flt(doc.amount) + 50, 2}",
		}
		jinja = self.handler._compile_structured_value_to_jinja(val)
		self.assertEqual(jinja, "{{ frappe.utils.flt(doc.amount) + 50, 2 }}")

	def test_compile_format_resolver(self):
		val = {
			"mode": "resolver",
			"config": {
				"kind": "format",
				"fmt_op": "format_date",
				"fmt_field": "creation",
				"fmt_config": "YYYY-MM-DD",
			},
		}
		jinja = self.handler._compile_structured_value_to_jinja(val)
		# Should use format helper
		self.assertIn('format("format_date"', jinja)
		self.assertIn('"fmt_op": "format_date"', jinja)

	def test_compile_normalize_resolver(self):
		val = {
			"mode": "resolver",
			"config": {"kind": "normalization", "norm_op": "upper", "norm_field": "first_name"},
		}
		jinja = self.handler._compile_structured_value_to_jinja(val)
		# Should use normalize helper
		self.assertIn("normalize(value", jinja)
		self.assertIn('["upper"]', jinja)
