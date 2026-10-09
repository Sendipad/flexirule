# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.utils.frappe_query_compat import (
	QUERY_CAPABILITIES,
	FrappeQueryCapabilities,
	execute_query,
)


class TestFrappeQueryCompat(FrappeTestCase):
	def test_capabilities_are_detected_from_installed_engine(self):
		from inspect import signature

		expected = "ignore_permissions" in signature(frappe.database.query.Engine.get_query).parameters
		self.assertEqual(QUERY_CAPABILITIES.supports_ignore_permissions, expected)

	def test_capability_detection_is_not_used_on_hot_path(self):
		query = MagicMock()
		query.run.return_value = [{"name": "Administrator"}]

		with patch(
			"flexirule.ruleflow.utils.frappe_query_compat.signature",
			side_effect=AssertionError("signature inspection must not run during execution"),
		):
			with patch("frappe.qb.get_query", return_value=query):
				result = execute_query("User", {"fields": ["name"]}, ignore_permissions=True)

		self.assertEqual(result, [{"name": "Administrator"}])

	def test_native_permission_capability_is_passed_through(self):
		query = MagicMock()
		query.run.return_value = [{"name": "Administrator"}]

		with patch(
			"flexirule.ruleflow.utils.frappe_query_compat.QUERY_CAPABILITIES",
			FrappeQueryCapabilities(
				supports_ignore_permissions=True,
				supports_logical_filter_groups=True,
			),
		):
			with patch("frappe.qb.get_query", return_value=query) as get_query:
				result = execute_query("User", {"fields": ["name"], "limit": 10, "offset": 2}, False)

		self.assertEqual(result, [{"name": "Administrator"}])
		self.assertEqual(get_query.call_args.kwargs["ignore_permissions"], False)
		self.assertEqual(get_query.call_args.kwargs["limit"], 10)
		self.assertEqual(get_query.call_args.kwargs["offset"], 2)

	def test_legacy_permission_path_does_not_pass_unsupported_argument(self):
		query = MagicMock()
		query.where.return_value = query
		query.run.return_value = [{"name": "Administrator"}]

		with patch(
			"flexirule.ruleflow.utils.frappe_query_compat.QUERY_CAPABILITIES",
			FrappeQueryCapabilities(
				supports_ignore_permissions=False,
				supports_logical_filter_groups=True,
			),
		):
			with patch("frappe.qb.get_query", return_value=query) as get_query:
				with patch(
					"flexirule.ruleflow.utils.frappe_query_compat.Permission.check_permissions"
				) as check_permissions:
					with patch(
						"flexirule.ruleflow.utils.frappe_query_compat._get_permission_condition",
						return_value="tabUser.name != 'blocked'",
					):
						result = execute_query("User", {"fields": ["name"]}, False)

		self.assertEqual(result, [{"name": "Administrator"}])
		self.assertNotIn("ignore_permissions", get_query.call_args.kwargs)
		check_permissions.assert_called_once()

	def test_legacy_logical_filters_are_compiled_to_native_criterion(self):
		query = MagicMock()
		query.run.return_value = [{"name": "Administrator"}]

		filters = [
			["enabled", "=", 1],
			"or",
			["email", "like", "%@example.com"],
		]

		with patch(
			"flexirule.ruleflow.utils.frappe_query_compat.QUERY_CAPABILITIES",
			FrappeQueryCapabilities(
				supports_ignore_permissions=False,
				supports_logical_filter_groups=False,
			),
		):
			with patch("frappe.qb.get_query", return_value=query) as get_query:
				with patch("flexirule.ruleflow.utils.frappe_query_compat.Permission.check_permissions"):
					with patch(
						"flexirule.ruleflow.utils.frappe_query_compat._get_permission_condition",
						return_value="",
					):
						execute_query("User", {"filters": filters}, False)

		compiled = get_query.call_args.kwargs["filters"]
		self.assertNotIsInstance(compiled, list)
		self.assertIn(" OR ", compiled.get_sql().upper())

	def test_limit_and_offset_are_not_rewritten_on_legacy_path(self):
		query = MagicMock()
		query.run.return_value = []

		with patch(
			"flexirule.ruleflow.utils.frappe_query_compat.QUERY_CAPABILITIES",
			FrappeQueryCapabilities(
				supports_ignore_permissions=False,
				supports_logical_filter_groups=True,
			),
		):
			with patch("frappe.qb.get_query", return_value=query) as get_query:
				with patch("flexirule.ruleflow.utils.frappe_query_compat.Permission.check_permissions"):
					with patch(
						"flexirule.ruleflow.utils.frappe_query_compat._get_permission_condition",
						return_value="",
					):
						execute_query(
							"User",
							{"fields": ["name"], "limit": 50, "offset": 100},
							False,
						)

		self.assertEqual(get_query.call_args.kwargs["limit"], 50)
		self.assertEqual(get_query.call_args.kwargs["offset"], 100)
