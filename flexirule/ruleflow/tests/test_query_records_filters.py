# Copyright (c) 2026, FlexiRule and contributors

import unittest
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.core.action_handlers.query_records import QueryRecordsHandler


class TestQueryRecordsFilters(FrappeTestCase):
	def setUp(self):
		self.handler = QueryRecordsHandler()
		self.context = {
			"doc": frappe._dict({"status": "Open", "limit_val": 10}),
			"vars": {"search_term": "Flexi", "min_amount": 50, "max_amount": 100},
		}
		self.action = frappe._dict({"name": "ACT001", "label": "TestQuery", "config": "{}"})
		# Clear resolver cache
		if hasattr(frappe.local, "flexirule_compiled_resolvers"):
			delattr(frappe.local, "flexirule_compiled_resolvers")

	def test_resolve_simple_dict_filters(self):
		# Let's test with resolvers which is the recommended way
		config = {
			"filters": {
				"status": {"mode": "variable", "path": "doc.status"},
				"amount": [
					"Between",
					[
						{"mode": "variable", "path": "vars.min_amount"},
						{"mode": "variable", "path": "vars.max_amount"},
					],
				],
			}
		}

		filters, _ = self.handler._resolve_query_filters(config, self.context, self.action)

		# Should be normalized to [[field, op, val], ...]
		self.assertIn(["status", "=", "Open"], filters)
		# amount should be normalized to ['amount', 'between', [50, 100]]
		self.assertIn(["amount", "between", [50, 100]], filters)

	def test_resolve_list_of_dict_filters(self):
		config = {
			"filters": [
				{"fieldname": "status", "operator": "=", "value": {"mode": "variable", "path": "doc.status"}},
				{"field": "name", "operator": "like", "value": "{vars.search_term}%"},
			]
		}
		filters, _ = self.handler._resolve_query_filters(config, self.context, self.action)

		self.assertIn(["status", "=", "Open"], filters)
		self.assertIn(["name", "like", "Flexi%"], filters)

	def test_operator_normalization(self):
		config = {
			"filters": [
				["name", "starts with", "ABC"],
				["name", "ends with", "XYZ"],
				["amount", "Between", [10, 20]],
			]
		}
		filters, _ = self.handler._resolve_query_filters(config, self.context, self.action)

		self.assertIn(["name", "like", "ABC%"], filters)
		self.assertIn(["name", "like", "%XYZ"], filters)
		self.assertIn(["amount", "between", [10, 20]], filters)

	def test_timespan_normalization(self):
		config = {"filters": [["creation", "Timespan", "today"]]}
		# Patch nowdate in the module where it is imported
		with patch(
			"flexirule.ruleflow.core.action_handlers.query_records.nowdate", return_value="2026-05-20"
		):
			filters, _ = self.handler._resolve_query_filters(config, self.context, self.action)
			self.assertEqual(filters[0][1], "between")
			# [getdate("2026-05-20"), getdate("2026-05-20")]
			self.assertEqual(str(filters[0][2][0]), "2026-05-20")

	def test_boolean_payload_extraction(self):
		config = {"filters": [["is_active", "=", {"value": "Yes", "value_type": "Boolean"}]]}
		filters, _ = self.handler._resolve_query_filters(config, self.context, self.action)
		self.assertEqual(filters[0][2], 1)

		config["filters"] = [["is_active", "=", {"value": "false", "value_type": "Boolean"}]]
		filters, _ = self.handler._resolve_query_filters(config, self.context, self.action)
		self.assertEqual(filters[0][2], 0)

	def test_nested_resolver_in_filters(self):
		# Complex resolver inside a filter
		config = {
			"filters": {
				"total": {
					"mode": "resolver",
					"config": {
						"kind": "math_formula",
						"field_a": "doc.limit_val",
						"math_op": "*",
						"field_b_type": "constant",
						"constant_b": 2,
					},
				}
			}
		}
		filters, _ = self.handler._resolve_query_filters(config, self.context, self.action)
		self.assertEqual(filters[0][2], 20.0)

	def test_interpolation_in_filters(self):
		config = {"filters": [["description", "like", "Status is {doc.status} for {vars.search_term}"]]}
		filters, _ = self.handler._resolve_query_filters(config, self.context, self.action)
		self.assertEqual(filters[0][2], "Status is Open for Flexi")

	def test_canonical_filter_tree_normalizes_for_query_list(self):
		config = {
			"filters": {
				"type": "group",
				"operator": "or",
				"children": [
					{
						"type": "leaf",
						"doctype": "User",
						"field": "first_name",
						"operator": "starts with",
						"value": {"mode": "static", "value": "Admin"},
					},
					{
						"type": "leaf",
						"doctype": "User",
						"field": "enabled",
						"operator": "=",
						"value": {"mode": "static", "value": 1},
					},
				],
			}
		}
		with patch("frappe.get_list", return_value=[]) as mock_get_list:
			self.handler._query_list("User", config, self.context, self.action, ignore_permissions=True)

		mock_get_list.assert_called_once()
		self.assertEqual(
			mock_get_list.call_args.kwargs["filters"],
			[
				["User", "first_name", "like", "Admin%"],
				"or",
				["User", "enabled", "=", 1],
			],
		)

	def test_canonical_filter_tree_normalizes_for_fetch_records(self):
		config = {
			"filters": {
				"type": "group",
				"operator": "or",
				"children": [
					{
						"type": "leaf",
						"doctype": "User",
						"field": "first_name",
						"operator": "starts with",
						"value": {"mode": "static", "value": "Admin"},
					},
					{
						"type": "leaf",
						"doctype": "User",
						"field": "enabled",
						"operator": "=",
						"value": {"mode": "static", "value": 1},
					},
				],
			}
		}
		action = frappe._dict(
			{
				"operation": "Fetch Records",
				"reference_doctype": "User",
				"ignore_permissions": 1,
				"permission_audit_reason": "Test canonical filter normalization",
				"config": frappe.as_json(config),
			}
		)

		with patch(
			"flexirule.ruleflow.utils.frappe_query_compat.execute_query", return_value=[]
		) as execute_query:
			self.handler.execute(action, self.context, None)

		execute_query.assert_called_once()
		self.assertEqual(
			execute_query.call_args.args[1]["filters"],
			[
				["first_name", "like", "Admin%"],
				"or",
				["enabled", "=", 1],
			],
		)

	@patch("frappe.get_list")
	def test_query_list_integration(self, mock_get_list):
		config = {
			"filters": {"status": {"mode": "variable", "path": "doc.status"}},
			"fields": ["name", "status"],
			"limit_type": "Custom Limit",
			"limit": 5,
		}
		self.handler._query_list("User", config, self.context, self.action, ignore_permissions=True)

		mock_get_list.assert_called_once()
		args = mock_get_list.call_args[1]
		self.assertEqual(args["doctype"], "User")
		self.assertEqual(args["filters"], [["status", "=", "Open"]])
		self.assertEqual(args["limit_page_length"], 5)
		self.assertEqual(args["fields"], ["name", "status"])

	def test_resolve_filters_with_context_edge_cases(self):
		# Test None filters
		self.assertIsNone(self.handler._resolve_filters_with_context(None, self.context, "test"))

		# Test plain values in list
		config_filters_list = ["direct_value", 123]
		resolved_list = self.handler._resolve_filters_with_context(config_filters_list, self.context, "test")
		self.assertEqual(resolved_list, ["direct_value", 123])

		# Test dictionary with no mode
		config_filters_dict = {"a": 1, "b": 2}
		resolved_dict = self.handler._resolve_filters_with_context(config_filters_dict, self.context, "test")
		self.assertEqual(resolved_dict, {"a": 1, "b": 2})

	def test_or_filters_resolution(self):
		config = {
			"filters": {"status": "Open"},
			"or_filters": [
				["priority", "=", {"mode": "static", "value": "High"}],
				{"field": "owner", "operator": "=", "value": "{doc.status}"},
			],
		}
		with patch("frappe.session", frappe._dict({"user": "admin@example.com"})):
			filters, or_filters = self.handler._resolve_query_filters(config, self.context, self.action)

			self.assertEqual(filters, [["status", "=", "Open"]])
			self.assertIn(["priority", "=", "High"], or_filters)
			self.assertIn(["owner", "=", "Open"], or_filters)

	def test_child_table_filter_normalization(self):
		# Test dotted syntax roles.role on User DocType (core Frappe DocType with Has Role child table)
		config = {
			"filters": [
				["roles.role", "=", "System Manager"],
				{"doctype": "roles", "field": "role", "operator": "=", "value": "Script Manager"},
				["enabled", "=", 1],
			]
		}
		filters, _ = self.handler._resolve_query_filters(
			config, self.context, self.action, reference_doctype="User"
		)

		self.assertIn(["Has Role", "role", "=", "System Manager"], filters)
		self.assertIn(["Has Role", "role", "=", "Script Manager"], filters)
		self.assertIn(["enabled", "=", 1], filters)

	def test_child_table_query_execution_all_modes(self):
		# Test User DocType with child table roles (Has Role)
		config = {"filters": [["roles.role", "=", "System Manager"]]}

		# 1. Query List
		res_list = self.handler._query_list(
			"User", config, self.context, self.action, ignore_permissions=True
		)
		self.assertTrue(isinstance(res_list, list))

		# 2. Count
		res_count = self.handler._count_records(
			"User", config, self.context, self.action, ignore_permissions=True
		)
		self.assertGreaterEqual(res_count, 1)

		# 3. Exist Record
		res_exist = self.handler._exist_record(
			"User", config, self.context, self.action, ignore_permissions=True
		)
		self.assertTrue(res_exist)

		# 4. Aggregate
		self.action.operation = "Sum"
		config_sum = {"filters": [["roles.role", "=", "System Manager"]], "field": "enabled"}
		res_sum = self.handler._aggregate(
			"User", config_sum, self.context, self.action, ignore_permissions=True
		)
		self.assertGreaterEqual(res_sum, 1)

		# 5. Group By
		self.action.operation = "Group By"
		config_gb = {
			"filters": [["roles.role", "=", "System Manager"]],
			"field": "name",
			"group_by_field": "roles.role",
		}
		res_gb = self.handler._group_by("User", config_gb, self.context, self.action, ignore_permissions=True)
		self.assertTrue(isinstance(res_gb, list))
		self.assertEqual(res_gb[0].get("role"), "System Manager")


class TestFetchRecordsCanonicalFilterContract(FrappeTestCase):
	def setUp(self):
		self.handler = QueryRecordsHandler()
		self.context = {"doc": frappe._dict(), "vars": {}}
		self.action = frappe._dict({"name": "CANONICAL_TEST", "label": "Canonical test", "config": "{}"})

	def test_nested_canonical_tree_converts_to_native_filters(self):
		tree = {
			"type": "group",
			"operator": "and",
			"children": [
				{
					"type": "leaf",
					"doctype": "User",
					"field": "enabled",
					"operator": "=",
					"value": {"mode": "static", "value": 1},
				},
				{
					"type": "group",
					"operator": "or",
					"children": [
						{
							"type": "leaf",
							"doctype": "User",
							"field": "first_name",
							"operator": "starts with",
							"value": {"mode": "static", "value": "Ada"},
						},
						{
							"type": "leaf",
							"doctype": "User",
							"field": "last_name",
							"operator": "in",
							"value": {"mode": "static", "value": ["Lovelace", "Hopper"]},
						},
					],
				},
			],
		}
		self.assertEqual(self.handler._validate_canonical_fetch_filter_tree(tree), [])
		self.assertEqual(
			self.handler._canonical_filter_tree_to_backend(tree, "User"),
			[
				["User", "enabled", "=", 1],
				"and",
				[
					["User", "first_name", "like", "Ada%"],
					"or",
					["User", "last_name", "in", ["Lovelace", "Hopper"]],
				],
			],
		)

	def test_rejects_legacy_filter_shapes_for_fetch_records(self):
		for payload in (
			[["enabled", "=", 1]],
			{"enabled": 1},
			[{"field": "enabled", "operator": "=", "value": 1}],
		):
			with self.subTest(payload=payload):
				self.assertTrue(self.handler._validate_canonical_fetch_filter_tree(payload))

	def test_rejects_malformed_canonical_nodes(self):
		invalid_trees = [
			{"type": "group", "operator": "xor", "children": []},
			{
				"type": "group",
				"operator": "and",
				"children": [{"type": "leaf", "field": "", "operator": "=", "value": 1}],
			},
			{"type": "leaf", "field": "enabled", "operator": "contains", "value": "x"},
			{"type": "leaf", "field": "enabled", "operator": "=", "value": {"mode": "static"}},
			{"type": "leaf", "field": "enabled", "operator": "="},
		]
		for tree in invalid_trees:
			with self.subTest(tree=tree):
				self.assertTrue(self.handler._validate_canonical_fetch_filter_tree(tree))

	def test_serialized_fetch_records_config_uses_only_canonical_conversion(self):
		config = {
			"filters": {
				"type": "group",
				"operator": "and",
				"children": [
					{
						"type": "leaf",
						"doctype": "User",
						"field": "enabled",
						"operator": "=",
						"value": {"mode": "static", "value": 1},
					},
					{
						"type": "leaf",
						"doctype": "User",
						"field": "first_name",
						"operator": "like",
						"value": {"mode": "static", "value": "Ada%"},
					},
				],
			}
		}
		action = frappe._dict(
			{
				"operation": "Fetch Records",
				"reference_doctype": "User",
				"ignore_permissions": 1,
				"permission_audit_reason": "Canonical contract test",
				"label": "Canonical contract test",
				"config": frappe.as_json(config),
			}
		)
		with patch(
			"flexirule.ruleflow.utils.frappe_query_compat.execute_query", return_value=[{"name": "user-1"}]
		) as execute_query:
			result, _ = self.handler.execute(action, self.context, None)
		self.assertEqual(result, [{"name": "user-1"}])
		self.assertEqual(
			execute_query.call_args.args[1]["filters"],
			[["enabled", "=", 1], "and", ["first_name", "like", "Ada%"]],
		)

	def test_legacy_in_not_in_null_empty_and_wildcard_semantics_remain_normalized(self):
		config = {
			"filters": [
				["name", "in", ["A", "B"]],
				["name", "not in", ["C", "D"]],
				["description", "=", None],
				["first_name", "=", ""],
				["last_name", "starts with", "Sm"],
				["email", "ends with", "@example.test"],
			]
		}
		filters, _ = self.handler._resolve_query_filters(
			config, self.context, self.action, reference_doctype="User"
		)
		self.assertIn(["name", "in", ["A", "B"]], filters)
		self.assertIn(["name", "not in", ["C", "D"]], filters)
		self.assertIn(["description", "=", None], filters)
		self.assertIn(["first_name", "=", ""], filters)
		self.assertIn(["last_name", "like", "Sm%"], filters)
		self.assertIn(["email", "like", "%@example.test"], filters)
