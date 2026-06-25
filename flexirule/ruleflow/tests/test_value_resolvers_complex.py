# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

import unittest
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.core.value_resolver import (
	ChildAggregationResolver,
	DateDiffResolver,
	DateFormulaResolver,
	ExpressionResolver,
	JinjaResolver,
	SafeEvalResolver,
	StaticResolver,
	StringFormulaResolver,
	SystemContextResolver,
	ValueResolver,
	VariableResolver,
)


class TestValueResolversComplex(FrappeTestCase):
	def setUp(self):
		self.context = {
			"doc": frappe._dict(
				{
					"creation": "2026-01-01",
					"amount": 100,
					"items": [
						{"qty": 2, "price": 10},
						{"qty": 1, "price": 20},
					],
				}
			),
			"vars": {"test_var": "test_val"},
		}

	def test_date_formula_resolver(self):
		# Today + 5 days
		with patch("frappe.utils.nowdate", return_value="2026-01-01"):
			resolver = DateFormulaResolver(
				base_type="today", base_field=None, offset_value=5, offset_unit="days", offset_sign="+"
			)
			self.assertEqual(str(resolver.resolve(self.context)), "2026-01-06")

			# Today - 5 days
			resolver = DateFormulaResolver(
				base_type="today", base_field=None, offset_value=5, offset_unit="days", offset_sign="-"
			)
			self.assertEqual(str(resolver.resolve(self.context)), "2025-12-27")

		# From field + 1 month
		resolver = DateFormulaResolver(
			base_type="field",
			base_field="doc.creation",
			offset_value=1,
			offset_unit="months",
			offset_sign="+",
		)
		self.assertEqual(str(resolver.resolve(self.context)), "2026-02-01")

		# Leap year test: 2024-02-28 + 1 day
		self.context["doc"]["creation"] = "2024-02-28"
		resolver = DateFormulaResolver(
			base_type="field", base_field="doc.creation", offset_value=1, offset_unit="days", offset_sign="+"
		)
		self.assertEqual(str(resolver.resolve(self.context)), "2024-02-29")

		# Month rollover: 2026-01-31 + 1 month -> 2026-02-28
		self.context["doc"]["creation"] = "2026-01-31"
		resolver = DateFormulaResolver(
			base_type="field",
			base_field="doc.creation",
			offset_value=1,
			offset_unit="months",
			offset_sign="+",
		)
		self.assertEqual(str(resolver.resolve(self.context)), "2026-02-28")

		# Null base date
		self.context["doc"]["creation"] = None
		resolver = DateFormulaResolver(
			base_type="field", base_field="doc.creation", offset_value=1, offset_unit="days", offset_sign="+"
		)
		self.assertIsNone(resolver.resolve(self.context))

	def test_date_diff_resolver(self):
		# Diff in days
		resolver = DateDiffResolver(
			diff_start_type="field",
			diff_start_field="doc.start",
			diff_end_type="field",
			diff_end_field="doc.end",
			diff_unit="days",
		)
		self.context["doc"].update({"start": "2026-01-01", "end": "2026-01-11"})
		self.assertEqual(resolver.resolve(self.context), 10)

		# Diff in months
		# frappe.utils.month_diff is inclusive, 2026-01-01 to 2026-03-01 -> 3 months
		self.context["doc"].update({"start": "2026-01-01", "end": "2026-03-01"})
		resolver.diff_unit = "months"
		self.assertEqual(resolver.resolve(self.context), 3)

		# Diff in years
		# frappe.utils.month_diff returns months + 1 (it's inclusive)
		# 2028-01-01 to 2026-01-01 -> 25 months -> int(25/12) = 2 years
		self.context["doc"].update({"start": "2026-01-01", "end": "2028-01-01"})
		resolver.diff_unit = "years"
		self.assertEqual(resolver.resolve(self.context), 2)

		# Today comparison
		with patch("frappe.utils.nowdate", return_value="2026-01-15"):
			resolver = DateDiffResolver(
				diff_start_type="field",
				diff_start_field="doc.start",
				diff_end_type="today",
				diff_end_field=None,
				diff_unit="days",
			)
			self.context["doc"]["start"] = "2026-01-01"
			self.assertEqual(resolver.resolve(self.context), 14)

		# Missing dates
		self.context["doc"]["start"] = None
		self.assertEqual(resolver.resolve(self.context), 0)

	def test_child_aggregation_resolver(self):
		# Sum
		resolver = ChildAggregationResolver(agg_table="doc.items", agg_field="qty", agg_op="sum")
		self.assertEqual(resolver.resolve(self.context), 3.0)

		# Count
		resolver.agg_op = "count"
		self.assertEqual(resolver.resolve(self.context), 2)

		# Avg
		resolver.agg_op = "avg"
		self.assertEqual(resolver.resolve(self.context), 1.5)

		# Empty table
		self.context["doc"]["items"] = []
		resolver.agg_op = "sum"
		self.assertEqual(resolver.resolve(self.context), 0)

		# Table is None
		self.context["doc"]["items"] = None
		self.assertEqual(resolver.resolve(self.context), 0)

		# agg_field is None for some rows
		self.context["doc"]["items"] = [{"qty": 5}, {"other": 10}]
		resolver.agg_op = "sum"
		self.assertEqual(resolver.resolve(self.context), 5.0)

	def test_string_formula_resolver(self):
		# Concat fields
		resolver = StringFormulaResolver(
			str_op="concat", str_a_type="field", str_a="doc.first", str_b_type="field", str_b="doc.last"
		)
		self.context["doc"].update({"first": "John", "last": "Doe"})
		self.assertEqual(resolver.resolve(self.context), "JohnDoe")

		# Uppercase
		resolver = StringFormulaResolver(
			str_op="uppercase", str_a_type="field", str_a="doc.first", str_b_type="constant", str_b=None
		)
		self.assertEqual(resolver.resolve(self.context), "JOHN")

		# Lowercase
		resolver.str_op = "lowercase"
		self.assertEqual(resolver.resolve(self.context), "john")

		# Money format
		resolver = StringFormulaResolver(
			str_op="fmt_money", str_a_type="field", str_a="doc.amount", str_b_type="constant", str_b="USD"
		)
		self.context["doc"]["amount"] = 100
		res = resolver.resolve(self.context)
		self.assertIn("100", res)

	def test_system_context_resolver(self):
		# User
		# Use frappe.session directly instead of patching a member that might be a property or None
		with patch("frappe.session", frappe._dict({"user": "test@example.com"})):
			resolver = SystemContextResolver(sys_token="user", sys_role="")
			self.assertEqual(resolver.resolve(self.context), "test@example.com")

		# Role check
		with patch("frappe.get_roles", return_value=["System Manager", "Rule Manager"]):
			with patch("frappe.session", frappe._dict({"user": "test@example.com"})):
				resolver = SystemContextResolver(sys_token="role_check", sys_role="System Manager")
				self.assertTrue(resolver.resolve(self.context))

				resolver = SystemContextResolver(sys_token="role_check", sys_role="Guest")
				self.assertFalse(resolver.resolve(self.context))

	def test_jinja_resolver(self):
		resolver = JinjaResolver(template="Hello {{ doc.first }}!")
		self.context["doc"]["first"] = "Jules"
		self.assertEqual(resolver.resolve(self.context), "Hello Jules!")

	def test_safe_eval_resolver(self):
		resolver = SafeEvalResolver(expression="doc.amount * 2")
		self.context["doc"]["amount"] = 50
		self.assertEqual(resolver.resolve(self.context), 100)

	def test_expression_resolver(self):
		# Mixed text and variable
		segments = [StaticResolver("Val: "), VariableResolver("vars.test_var"), StaticResolver("!")]
		resolver = ExpressionResolver(segments)
		self.assertEqual(resolver.resolve(self.context), "Val: test_val!")

		# None handling in expression
		segments.append(VariableResolver("non_existent"))
		self.assertEqual(resolver.resolve(self.context), "Val: test_val!")

	def test_value_resolver_compile_expression_complex(self):
		# Test compiling a complex expression with various token types
		val = {
			"mode": "expression",
			"value": [
				{"type": "text", "value": "Date: "},
				{
					"type": "resolverToken",
					"attrs": {
						"config": {
							"kind": "format",
							"fmt_op": "format_date",
							"fmt_field": "doc.creation",
							"fmt_config": "yyyy",
						}
					},
				},
				{"type": "text", "value": " - "},
				{"type": "jsonToken", "attrs": {"value": "{{ doc.first }}"}},
			],
		}
		self.context["doc"].update({"creation": "2026-05-20", "first": "Jules"})
		resolver = ValueResolver.compile(val)
		self.assertIsInstance(resolver, ExpressionResolver)
		self.assertEqual(resolver.resolve(self.context), "Date: 2026 - Jules")

	def test_value_resolver_compile_resolver_token_eval(self):
		# Test resolverToken with expression/resolver instead of config
		val = {
			"mode": "expression",
			"value": [{"type": "resolverToken", "attrs": {"expression": "doc.amount + 10"}}],
		}
		self.context["doc"]["amount"] = 90
		resolver = ValueResolver.compile(val)
		self.assertEqual(resolver.resolve(self.context), "100")
