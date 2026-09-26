# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

import unittest

import frappe

from flexirule.ruleflow.core.exceptions import MethodExecutionError
from flexirule.ruleflow.core.value_resolver import (
	CollectionResolver,
	ValueResolver,
)


class TestCollectionResolver(unittest.TestCase):
	def setUp(self):
		self.items = [
			{"item_code": "ITEM-A", "qty": 10, "rate": 100, "category": "Hardware"},
			{"item_code": "ITEM-B", "qty": 50, "rate": 200, "category": "Software"},
			{"item_code": "ITEM-C", "qty": 120, "rate": 150, "category": "Hardware"},
			{"item_code": "ITEM-A", "qty": 30, "rate": 100, "category": "Hardware"},
		]
		self.context = {
			"doc": frappe._dict({"name": "SO-0001", "status": "Draft", "items": self.items}),
			"vars": {"custom_list": [{"code": "X", "val": 1}, {"code": "Y", "val": 2}]},
		}

	def test_count_operation(self):
		# Unfiltered count
		res_unfiltered = CollectionResolver(source="doc.items", operation="count")
		self.assertEqual(res_unfiltered.resolve(self.context), 4)

		# Filtered count (qty > 20)
		cond = [{"left": {"ref": "row.qty"}, "op": ">", "right": {"value": 20}}]
		res_filtered = CollectionResolver(source="doc.items", operation="count", condition=cond)
		self.assertEqual(res_filtered.resolve(self.context), 3)

	def test_any_operation(self):
		# True case (qty > 100)
		cond_true = [{"left": {"ref": "row.qty"}, "op": ">", "right": {"value": 100}}]
		res_true = CollectionResolver(source="doc.items", operation="any", condition=cond_true)
		self.assertTrue(res_true.resolve(self.context))

		# False case (qty > 500)
		cond_false = [{"left": {"ref": "row.qty"}, "op": ">", "right": {"value": 500}}]
		res_false = CollectionResolver(source="doc.items", operation="any", condition=cond_false)
		self.assertFalse(res_false.resolve(self.context))

	def test_all_operation(self):
		# True case (qty > 0)
		cond_true = [{"left": {"ref": "row.qty"}, "op": ">", "right": {"value": 0}}]
		res_true = CollectionResolver(source="doc.items", operation="all", condition=cond_true)
		self.assertTrue(res_true.resolve(self.context))

		# False case (qty > 20)
		cond_false = [{"left": {"ref": "row.qty"}, "op": ">", "right": {"value": 20}}]
		res_false = CollectionResolver(source="doc.items", operation="all", condition=cond_false)
		self.assertFalse(res_false.resolve(self.context))

	def test_first_and_find_alias(self):
		cond = [{"left": {"ref": "row.category"}, "op": "==", "right": {"value": "Software"}}]

		res_first = CollectionResolver(source="doc.items", operation="first", condition=cond)
		first_match = res_first.resolve(self.context)
		self.assertIsNotNone(first_match)
		self.assertEqual(first_match["item_code"], "ITEM-B")

		# 'find' operation must behave identically to 'first'
		res_find = CollectionResolver(source="doc.items", operation="find", condition=cond)
		find_match = res_find.resolve(self.context)
		self.assertEqual(first_match, find_match)

	def test_filter_operation(self):
		cond = [{"left": {"ref": "row.category"}, "op": "==", "right": {"value": "Hardware"}}]
		res = CollectionResolver(source="doc.items", operation="filter", condition=cond)
		filtered = res.resolve(self.context)
		self.assertEqual(len(filtered), 3)
		self.assertTrue(all(r["category"] == "Hardware" for r in filtered))

	def test_pluck_operation(self):
		res = CollectionResolver(source="doc.items", operation="pluck", target_field="item_code")
		codes = res.resolve(self.context)
		self.assertEqual(codes, ["ITEM-A", "ITEM-B", "ITEM-C", "ITEM-A"])

	def test_unique_operation(self):
		res = CollectionResolver(source="doc.items", operation="unique", target_field="item_code")
		unique_codes = res.resolve(self.context)
		self.assertEqual(unique_codes, ["ITEM-A", "ITEM-B", "ITEM-C"])

	def test_vars_context(self):
		res = CollectionResolver(source="vars.custom_list", operation="pluck", target_field="code")
		codes = res.resolve(self.context)
		self.assertEqual(codes, ["X", "Y"])

	def test_missing_and_empty_collection(self):
		# Non-existent path
		res_missing = CollectionResolver(source="doc.non_existent", operation="count")
		self.assertEqual(res_missing.resolve(self.context), 0)

		res_missing_filter = CollectionResolver(source="doc.non_existent", operation="filter")
		self.assertEqual(res_missing_filter.resolve(self.context), [])

		res_missing_all = CollectionResolver(source="doc.non_existent", operation="all")
		self.assertFalse(res_missing_all.resolve(self.context))

		res_missing_any = CollectionResolver(source="doc.non_existent", operation="any")
		self.assertFalse(res_missing_any.resolve(self.context))

		# Empty list in context
		ctx_empty = {"doc": frappe._dict({"items": []})}
		res_empty_all = CollectionResolver(source="doc.items", operation="all")
		self.assertTrue(res_empty_all.resolve(ctx_empty))

		res_empty_count = CollectionResolver(source="doc.items", operation="count")
		self.assertEqual(res_empty_count.resolve(ctx_empty), 0)

	def test_row_limit_guard(self):
		huge_collection = [{"id": i} for i in range(10001)]
		ctx_huge = {"doc": frappe._dict({"items": huge_collection})}

		res = CollectionResolver(source="doc.items", operation="count")
		with self.assertRaises(MethodExecutionError):
			res.resolve(ctx_huge)

	def test_sum_operation(self):
		# Unfiltered sum of qty (10 + 50 + 120 + 30 = 210)
		res_sum = CollectionResolver(source="doc.items", operation="sum", target_field="qty")
		self.assertEqual(res_sum.resolve(self.context), 210)

		# Filtered sum (Hardware category: 10 + 120 + 30 = 160)
		cond = [{"left": {"ref": "row.category"}, "op": "==", "right": {"value": "Hardware"}}]
		res_filtered_sum = CollectionResolver(
			source="doc.items", operation="sum", target_field="qty", condition=cond
		)
		self.assertEqual(res_filtered_sum.resolve(self.context), 160)

	def test_avg_operation(self):
		# Unfiltered avg of rate (100 + 200 + 150 + 100) / 4 = 137.5
		res_avg = CollectionResolver(source="doc.items", operation="avg", target_field="rate")
		self.assertEqual(res_avg.resolve(self.context), 137.5)

		# Filtered avg (Hardware category: (100 + 150 + 100) / 3 = 116.66666666666667)
		cond = [{"left": {"ref": "row.category"}, "op": "==", "right": {"value": "Hardware"}}]
		res_filtered_avg = CollectionResolver(
			source="doc.items", operation="avg", target_field="rate", condition=cond
		)
		self.assertAlmostEqual(res_filtered_avg.resolve(self.context), 116.66666666666667)

	def test_child_aggregation_backward_compatibility(self):
		# Legacy child_aggregation payload format
		legacy_payload = {
			"mode": "resolver",
			"config": {
				"kind": "child_aggregation",
				"agg_table": "doc.items",
				"agg_field": "qty",
				"agg_op": "sum",
			},
		}
		compiled = ValueResolver.compile(legacy_payload)
		self.assertIsInstance(compiled, CollectionResolver)
		self.assertEqual(compiled.resolve(self.context), 210)

		# Legacy child_aggregation avg
		legacy_avg_payload = {
			"kind": "child_aggregation",
			"agg_table": "doc.items",
			"agg_field": "rate",
			"agg_op": "avg",
		}
		compiled_avg = ValueResolver.compile_resolver_config(legacy_avg_payload)
		self.assertEqual(compiled_avg.resolve(self.context), 137.5)

	def test_canonical_two_level_contract(self):
		canonical_payload = {
			"family": "collection",
			"operation": "sum",
			"config": {
				"source": "doc.items",
				"target_field": "qty",
				"condition": [{"left": {"ref": "row.category"}, "op": "==", "right": {"value": "Hardware"}}],
			},
		}
		compiled = ValueResolver.compile_resolver_config(canonical_payload)
		self.assertIsInstance(compiled, CollectionResolver)
		self.assertEqual(compiled.resolve(self.context), 160)

	def test_compiler_integration(self):
		config_payload = {
			"mode": "resolver",
			"config": {
				"kind": "collection",
				"source": "doc.items",
				"operation": "pluck",
				"target_field": "item_code",
			},
		}

		compiled = ValueResolver.compile(config_payload)
		self.assertIsInstance(compiled, CollectionResolver)
		self.assertEqual(compiled.resolve(self.context), ["ITEM-A", "ITEM-B", "ITEM-C", "ITEM-A"])
