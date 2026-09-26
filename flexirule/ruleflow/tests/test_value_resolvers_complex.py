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

	def test_date_family_resolver(self):
		# 1. Date Formula (calculate operation) via canonical payload
		val_calc = {
			"family": "date",
			"operation": "calculate",
			"config": {
				"base_type": "doc_field",
				"base_field": "doc.creation",
				"offset_value": 5,
				"offset_unit": "days",
				"offset_sign": "+",
			},
		}
		self.context["doc"]["creation"] = "2026-01-01"
		resolver = ValueResolver.compile_resolver_config(val_calc)
		self.assertIsInstance(resolver, DateFormulaResolver)
		self.assertEqual(str(resolver.resolve(self.context)), "2026-01-06")

		# Calculate Today - 3 days
		with patch("frappe.utils.nowdate", return_value="2026-01-10"):
			val_calc_today = {
				"family": "date",
				"operation": "calculate",
				"config": {
					"base_type": "today",
					"offset_value": 3,
					"offset_unit": "days",
					"offset_sign": "-",
				},
			}
			resolver = ValueResolver.compile(val_calc_today)
			self.assertEqual(str(resolver.resolve(self.context)), "2026-01-07")

		# 2. Date Difference (diff operation) via canonical payload
		val_diff = {
			"family": "date",
			"operation": "diff",
			"config": {
				"diff_start_type": "doc_field",
				"diff_start_field": "doc.start",
				"diff_end_type": "doc_field",
				"diff_end_field": "doc.end",
				"diff_unit": "days",
			},
		}
		self.context["doc"].update({"start": "2026-01-01", "end": "2026-01-11"})
		resolver = ValueResolver.compile_resolver_config(val_diff)
		self.assertIsInstance(resolver, DateDiffResolver)
		self.assertEqual(resolver.resolve(self.context), 10)

		# 3. Date Format (format operation) via canonical payload
		val_fmt = {
			"family": "date",
			"operation": "format",
			"config": {
				"fmt_field": "doc.creation",
				"fmt_config": "dd-mm-yyyy",
			},
		}
		self.context["doc"]["creation"] = "2026-01-01"
		resolver = ValueResolver.compile_resolver_config(val_fmt)
		self.assertEqual(resolver.resolve(self.context), "01-01-2026")

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

	def test_text_transform_resolver(self):
		# Combine operation via ValueResolver.compile
		val_combine = {
			"family": "text",
			"operation": "combine",
			"config": {
				"str_a_type": "field",
				"str_a": "doc.first",
				"str_b_type": "field",
				"str_b": "doc.last",
			},
		}
		self.context["doc"].update({"first": "John", "last": "Doe"})
		resolver = ValueResolver.compile_resolver_config(val_combine)
		self.assertEqual(resolver.resolve(self.context), "JohnDoe")

		# Case operation
		val_case = {
			"family": "text",
			"operation": "case",
			"config": {"field": "doc.first", "case_mode": "uppercase"},
		}
		resolver = ValueResolver.compile_resolver_config(val_case)
		self.assertEqual(resolver.resolve(self.context), "JOHN")

		# Normalize operation
		val_norm = {
			"family": "text",
			"operation": "normalize",
			"config": {"norm_field": "doc.raw", "norm_pipeline": ["trim", "lowercase"]},
		}
		self.context["doc"]["raw"] = "  HELLO WORLD  "
		resolver = ValueResolver.compile_resolver_config(val_norm)
		self.assertEqual(resolver.resolve(self.context), "hello world")

		# Format operation
		val_fmt = {
			"family": "text",
			"operation": "format",
			"config": {"fmt_field": "doc.first", "fmt_config": "Hello {0}!"},
		}
		resolver = ValueResolver.compile_resolver_config(val_fmt)
		self.assertEqual(resolver.resolve(self.context), "Hello John!")

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
				{"type": "text", "value": "Name: "},
				{
					"type": "resolverToken",
					"attrs": {
						"config": {
							"family": "text",
							"operation": "format",
							"config": {
								"fmt_field": "doc.first",
								"fmt_config": "{0}",
							},
						}
					},
				},
				{"type": "text", "value": " - "},
				{"type": "jsonToken", "attrs": {"value": "{{ doc.first }}"}},
			],
		}
		self.context["doc"].update({"first": "Jules"})
		resolver = ValueResolver.compile(val)
		self.assertIsInstance(resolver, ExpressionResolver)
		self.assertEqual(resolver.resolve(self.context), "Name: Jules - Jules")

	def test_value_resolver_compile_resolver_token_eval(self):
		# Test resolverToken with expression/resolver instead of config
		val = {
			"mode": "expression",
			"value": [{"type": "resolverToken", "attrs": {"expression": "doc.amount + 10"}}],
		}
		self.context["doc"]["amount"] = 90
		resolver = ValueResolver.compile(val)
		self.assertEqual(resolver.resolve(self.context), "100")
