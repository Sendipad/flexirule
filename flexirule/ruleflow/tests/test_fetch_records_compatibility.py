# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

import inspect
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.core.action_handlers.query_records import QueryRecordsHandler
from frappe.database.query import Engine


class TestFetchRecordsCompatibility(FrappeTestCase):
	def setUp(self):
		self.handler = QueryRecordsHandler()
		self.context = {"doc": frappe._dict({"status": "Open"}), "vars": {}}
		self.action = frappe._dict({"name": "ACT-FETCH", "label": "Fetch Records", "config": "{}"})

	def test_detects_nested_logical_filters(self):
		self.assertFalse(self.handler._has_logical_filter_operators({"status": "Open"}))
		self.assertTrue(
			self.handler._has_logical_filter_operators(
				[["status", "=", "Open"], "or", ["status", "=", "Pending"]]
			)
		)

	def test_legacy_filter_adapter_compiles_or_criteria(self):
		filters = [["status", "=", "Open"], "or", ["status", "=", "Pending"]]
		query = self.handler._get_query_with_legacy_filter_compat(
				"User",
				{"fields": ["name", "status"]},
				ignore_permissions=True,
				has_native_permissions=True,
		)
		# The helper is intentionally exercised through the same compiler path.
		criterion = self.handler._compile_legacy_filter_tree(Engine(), filters)
		self.assertIsNotNone(criterion)
		self.assertIn("OR", query.get_sql().upper() or "")
		self.assertIn("OR", str(criterion).upper() or "")

	def test_fetch_records_preserves_limit_and_offset(self):
		mock_query = MagicMock()
		mock_query.run.return_value = [{"name": "Administrator"}]
		config = {
			"fields": ["name"],
			"filters": [["enabled", "=", 1]],
			"limit": 10,
			"offset": 20,
		}
		with patch("flexirule.ruleflow.core.action_handlers.query_records.frappe.qb.get_query", return_value=mock_query) as get_query:
			result = self.handler._fetch_records(
				"User", config, self.context, self.action, ignore_permissions=True
			)
		self.assertEqual(result, [{"name": "Administrator"}])
		kwargs = get_query.call_args.kwargs
		self.assertEqual(kwargs["limit"], 10)
		self.assertEqual(kwargs["offset"], 20)
		self.assertEqual(kwargs["filters"], [["enabled", "=", 1]])

	def test_permission_fallback_for_old_engine_signature(self):
		mock_query = MagicMock()
		mock_query.run.return_value = []
		config = {"fields": ["name"], "filters": [["enabled", "=", 1]]}
		real_signature = inspect.signature

		def legacy_signature(target):
			if target is Engine.get_query:
				return inspect.Signature(
					[
						inspect.Parameter("self", inspect.Parameter.POSITIONAL_OR_KEYWORD),
						inspect.Parameter("table", inspect.Parameter.POSITIONAL_OR_KEYWORD),
					]
				)
			return real_signature(target)

		with (
			patch("flexirule.ruleflow.core.action_handlers.query_records.inspect.signature", side_effect=legacy_signature),
			patch("flexirule.ruleflow.core.action_handlers.query_records.frappe.qb.get_query", return_value=mock_query),
			patch(
				"flexirule.ruleflow.core.action_handlers.query_records.Permission.check_permissions"
			) as check_permissions,
		):
			self.handler._fetch_records(
				"User", config, self.context, self.action, ignore_permissions=False
			)

		check_permissions.assert_called_once_with(mock_query)
