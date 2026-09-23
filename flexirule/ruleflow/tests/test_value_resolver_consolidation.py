# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

import unittest

import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.core.value_resolver import (
	AggregateResolver,
	ConditionalResolver,
	DateResolver,
	LookupResolver,
	MathResolver,
	TextResolver,
	TypeConversionResolver,
	ValueResolver,
	ValueSourceResolver,
)


class TestValueResolverConsolidation(FrappeTestCase):
	def setUp(self):
		self.context = {
			"doc": frappe._dict(
				{
					"name": "TEST-001",
					"status": "Active",
					"grand_total": 1500.50,
					"posting_date": "2026-03-01",
					"items": [
						{"item_code": "ITEM-A", "qty": 10, "amount": 500.0},
						{"item_code": "ITEM-B", "qty": 5, "amount": 1000.5},
					],
				}
			),
			"vars": {"discount": 50.0, "code": "ABC"},
		}

	# 1. Value Source Resolver
	def test_value_source_resolver(self):
		res_field = ValueResolver.compile({"kind": "value_source", "operation": "field", "path": "doc.status"})
		self.assertEqual(res_field.resolve(self.context), "Active")

		res_var = ValueResolver.compile({"kind": "value_source", "operation": "variable", "path": "vars.discount"})
		self.assertEqual(res_var.resolve(self.context), 50.0)

		res_static = ValueResolver.compile({"kind": "value_source", "operation": "static", "value": "FixedValue"})
		self.assertEqual(res_static.resolve(self.context), "FixedValue")

	# 2. Date Resolver (Canonical & Legacy)
	def test_date_resolver(self):
		# Canonical Add
		res_add = ValueResolver.compile({
			"kind": "date",
			"operation": "add",
			"base_type": "doc_field",
			"base_field": "doc.posting_date",
			"offset_value": 5,
			"offset_unit": "days",
		})
		self.assertEqual(str(res_add.resolve(self.context)), "2026-03-06")

		# Canonical Diff
		res_diff = ValueResolver.compile({
			"kind": "date",
			"operation": "diff",
			"diff_start_type": "doc_field",
			"diff_start_field": "doc.posting_date",
			"diff_end_type": "doc_field",
			"diff_end_field": "doc.posting_date",
			"diff_unit": "days",
		})
		self.assertEqual(res_diff.resolve(self.context), 0)

		# Legacy date_formula payload
		res_legacy_formula = ValueResolver.compile({
			"kind": "date_formula",
			"base_type": "doc_field",
			"base_field": "doc.posting_date",
			"offset_value": 2,
			"offset_unit": "days",
			"offset_sign": "+",
		})
		self.assertEqual(str(res_legacy_formula.resolve(self.context)), "2026-03-03")

	# 3. Text Resolver
	def test_text_resolver(self):
		# Concat
		res_concat = ValueResolver.compile({
			"kind": "text",
			"operation": "concat",
			"field_a": "doc.name",
			"field_b": "vars.code",
		})
		self.assertEqual(res_concat.resolve(self.context), "TEST-001ABC")

		# Upper & Lower
		res_upper = ValueResolver.compile({"kind": "text", "operation": "upper", "field_a": "vars.code"})
		self.assertEqual(res_upper.resolve(self.context), "ABC")

		# Legacy string_formula payload
		res_legacy_str = ValueResolver.compile({
			"kind": "string_formula",
			"str_op": "uppercase",
			"str_a_type": "field",
			"str_a": "doc.name",
		})
		self.assertEqual(res_legacy_str.resolve(self.context), "TEST-001")

	# 4. Math Resolver
	def test_math_resolver(self):
		res_math = ValueResolver.compile({
			"kind": "math",
			"operation": "-",
			"field_a": "doc.grand_total",
			"field_b_type": "field",
			"field_b": "vars.discount",
		})
		self.assertEqual(res_math.resolve(self.context), 1450.50)

	# 5. Aggregate Resolver
	def test_aggregate_resolver(self):
		res_sum = ValueResolver.compile({
			"kind": "aggregate",
			"agg_table": "doc.items",
			"agg_field": "amount",
			"agg_op": "sum",
		})
		self.assertEqual(res_sum.resolve(self.context), 1500.50)

		res_count = ValueResolver.compile({
			"kind": "aggregate",
			"agg_table": "doc.items",
			"agg_op": "count",
		})
		self.assertEqual(res_count.resolve(self.context), 2)

	# 6. Lookup Resolver
	def test_lookup_resolver(self):
		res_lookup = ValueResolver.compile({
			"kind": "lookup",
			"operation": "get",
			"link_field": "doc.name",
			"linked_doctype": "User",
			"fetch_field": "email",
		})
		self.assertIsNone(res_lookup.resolve(self.context))

	# 7. Conditional Resolver
	def test_conditional_resolver(self):
		res_cond = ValueResolver.compile({
			"kind": "conditional",
			"condition": [{"field": "doc.status", "operator": "==", "value": "Active"}],
			"true_value": "YES",
			"false_value": "NO",
		})
		self.assertEqual(res_cond.resolve(self.context), "YES")

	# 8. Type Conversion Resolver
	def test_type_conversion_resolver(self):
		res_cast = ValueResolver.compile({
			"kind": "type_conversion",
			"operation": "integer",
			"field": "doc.grand_total",
		})
		self.assertEqual(res_cast.resolve(self.context), 1500)
