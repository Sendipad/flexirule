# Copyright (c) 2026, Abdo Ruzaqi and Contributors
# See license.txt

import json

import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.api import validate_rule_document


class TestRule(FrappeTestCase):
	def setUp(self):
		self.rule_name = "Test Validation Rule"
		if frappe.db.exists("Rule", self.rule_name):
			frappe.delete_doc("Rule", self.rule_name)

	def _insert_with_retry(self, doc, retries=3):
		import time

		last_error = None
		for _ in range(retries):
			try:
				return doc.insert(ignore_permissions=True)
			except frappe.QueryDeadlockError as e:
				last_error = e
				frappe.db.rollback()
				time.sleep(0.05)
		if last_error:
			raise last_error
		return doc

	def test_set_value_validation_gap(self):
		"""Verify that non-existent fields in Set Value action are blocked"""
		rule = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": self.rule_name,
				"document_type": "User",
				"trigger_type": "DocType Event",
				"trigger_event": "Before Save",
				"actions": [
					{
						"action_label": "Invalid Field Update",
						"action_type": "Assignment",
						"config": '[{"target": "doc.this_field_definitely_does_not_exist", "operator": "set", "value": "test"}]',
					}
				],
			}
		)

		with self.assertRaisesRegex(frappe.ValidationError, "does not exist on DocType"):
			rule.validate()

	def test_fetch_records_frappe15_bypass_is_normalized_on_standard_rule_save(self):
		"""Standard Desk form saves must apply the Frappe 15 Fetch Records default."""
		from unittest.mock import patch

		from flexirule.ruleflow.utils.frappe_query_compat import FrappeQueryCapabilities

		legacy_query_capabilities = FrappeQueryCapabilities(supports_ignore_permissions=False)
		rule = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": "Rule Fetch Records Permission Default",
				"document_type": "User",
				"trigger_type": "DocType Event",
				"trigger_event": "Before Save",
				"actions": [
					{
						"action_id": "root",
						"action_label": "Start",
						"action_type": "Entry Action",
						"is_enabled": 1,
						"next_step_if_true": "fetch_users",
					},
					{
						"action_id": "fetch_users",
						"action_label": "Fetch Users",
						"action_type": "Query Records",
						"operation": "Fetch Records",
						"reference_doctype": "User",
						"mutation_mode": "Set Context Variable",
						"return_type": "List of Records",
						"return_variable": "queried_users",
						"ignore_permissions": 0,
						"permission_audit_reason": "Approved Frappe 15 Fetch Records test",
						"config": frappe.as_json({"fields": ["name"], "limit": 10}),
						"is_enabled": 1,
						"next_step_if_true": "end",
					},
					{
						"action_id": "end",
						"action_label": "End",
						"action_type": "Stop",
						"operation": "Success",
						"is_enabled": 1,
					},
				],
			}
		)

		with (
			patch(
				"flexirule.ruleflow.core.validation_service.QUERY_CAPABILITIES",
				legacy_query_capabilities,
			),
			patch(
				"flexirule.ruleflow.core.action_handlers.query_records.QUERY_CAPABILITIES",
				legacy_query_capabilities,
			),
		):
			rule.validate()

			fetch_action = next(action for action in rule.actions if action.action_id == "fetch_users")
			self.assertEqual(int(fetch_action.ignore_permissions), 1)

			# The backend supplies the technical default, never the audit reason.
			fetch_action.permission_audit_reason = ""
			with self.assertRaisesRegex(frappe.ValidationError, "Permission Audit Reason"):
				rule.validate()

			self.assertEqual(int(fetch_action.ignore_permissions), 1)

	def test_consolidated_terminal_stop_success(self):
		"""Verify Stop Success action saves correctly without template"""
		rule = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": self.rule_name,
				"document_type": "User",
				"trigger_type": "DocType Event",
				"trigger_event": "Before Save",
				"actions": [{"action_label": "Stop Success", "action_type": "Stop", "operation": "Success"}],
			}
		)
		# Should not throw
		rule.validate()

	def test_consolidated_terminal_stop_error(self):
		"""Verify Stop Error action requires value_template"""
		rule = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": self.rule_name,
				"document_type": "User",
				"trigger_type": "DocType Event",
				"trigger_event": "Before Save",
				"is_active": 1,
				"actions": [
					{
						"action_id": "stop_1",
						"action_label": "Stop Error",
						"action_type": "Stop",
						"operation": "Error",
						"value_template": "",  # Empty
					}
				],
			}
		)

		with self.assertRaisesRegex(frappe.ValidationError, "requires field 'value_template'"):
			rule.validate()

		# Build a fresh doc with template and it should pass
		valid_rule = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": f"{self.rule_name} With Template",
				"document_type": "User",
				"trigger_type": "DocType Event",
				"trigger_event": "Before Save",
				"is_active": 1,
				"actions": [
					{
						"action_id": "stop_2",
						"action_label": "Stop Error",
						"action_type": "Stop",
						"operation": "Error",
						"value_template": "Critical Error!",
					}
				],
			}
		)
		valid_rule.validate()

	def test_service_matches_form_validation_for_missing_condition(self):
		"""API precheck and form validation should reject the same invalid rule definition."""
		payload = {
			"doctype": "Rule",
			"rule_name": "Rule Missing Condition",
			"document_type": "User",
			"trigger_type": "DocType Event",
			"trigger_event": "Before Save",
			"actions": [
				{
					"action_label": "Missing Condition",
					"action_type": "Condition",
					"action_id": "condition_1",
				}
			],
		}

		api_result = validate_rule_document(payload)
		self.assertFalse(api_result["valid"])
		self.assertTrue(
			any("is a Condition but no condition is defined" in error for error in api_result["errors"])
		)

		rule = frappe.get_doc(payload)
		with self.assertRaisesRegex(frappe.ValidationError, "is a Condition but no condition is defined"):
			rule.validate()

	def test_service_matches_form_validation_for_async_output_mapping(self):
		"""Async output mapping should fail consistently through API and form validation."""
		payload = {
			"doctype": "Rule",
			"rule_name": "Rule Async Output Mapping",
			"document_type": "User",
			"trigger_type": "DocType Event",
			"trigger_event": "Before Save",
			"actions": [
				{
					"action_label": "Async Query",
					"action_type": "Query Records",
					"action_id": "query_1",
					"reference_doctype": "User",
					"operation": "Query List",
					"is_async": 1,
					"config": '{"output_mapping":{"rows":"vars.rows"}}',
				}
			],
		}

		api_result = validate_rule_document(payload)
		self.assertFalse(api_result["valid"])
		self.assertTrue(
			any("cannot use Output Mapping with Async enabled" in error for error in api_result["errors"])
		)

		rule = frappe.get_doc(payload)
		with self.assertRaisesRegex(frappe.ValidationError, "cannot use Output Mapping with Async enabled"):
			rule.validate()

	def test_condition_compiles_for_non_canonical_action_type_value(self):
		"""Condition actions should compile even when action_type arrives in machine format."""
		rule = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": "Rule Condition Type Normalization",
				"document_type": "User",
				"trigger_type": "DocType Event",
				"trigger_event": "Before Save",
				"actions": [
					{
						"action_id": "root",
						"action_type": "Entry Action",
						"next_step_if_true": "condition_1",
					},
					{
						"action_id": "condition_1",
						"action_label": "New Condition",
						"action_type": "condition",
						"next_step_if_true": "stop_true",
						"next_step_if_false": "stop_false",
						"config": {
							"op": "and",
							"conditions": [
								{
									"left": {"ref": "doc.email"},
									"op": "is_not_set",
									"right": {"value": ""},
								}
							],
						},
					},
					{"action_id": "stop_true", "action_type": "Stop", "operation": "Success"},
					{"action_id": "stop_false", "action_type": "Stop", "operation": "Success"},
				],
			}
		)

		rule.validate()
		condition_action = next(a for a in rule.actions if a.action_id == "condition_1")
		self.assertTrue(condition_action.compiled_expression)

	def test_api_draft_validation_compiles_condition_payload(self):
		"""Draft precheck API should compile condition payload before handler validation."""
		payload = {
			"doctype": "Rule",
			"rule_name": "Rule API Draft Condition Compile",
			"document_type": "User",
			"trigger_type": "DocType Event",
			"trigger_event": "Before Save",
			"actions": [
				{"action_id": "root", "action_type": "Entry Action", "next_step_if_true": "condition_1"},
				{
					"action_id": "condition_1",
					"action_label": "New Condition",
					"action_type": "Condition",
					"next_step_if_true": "stop_true",
					"next_step_if_false": "stop_false",
					"config": {
						"op": "and",
						"conditions": [
							{
								"left": {"ref": "doc.email"},
								"op": "is_not_set",
								"right": {"value": ""},
							}
						],
					},
				},
				{"action_id": "stop_true", "action_type": "Stop", "operation": "Success"},
				{"action_id": "stop_false", "action_type": "Stop", "operation": "Success"},
			],
		}

		api_result = validate_rule_document(payload, mode="draft")
		self.assertTrue(api_result["valid"])

	def test_assignment_structured_literal_value_does_not_crash_variable_validation(self):
		"""Assignment value objects are config metadata, not Jinja template strings."""
		rule = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": "Rule Structured Assignment Value",
				"document_type": "User",
				"trigger_type": "DocType Event",
				"trigger_event": "Before Save",
				"actions": [
					{
						"action_id": "root",
						"action_type": "Entry Action",
						"next_step_if_true": "assignment_1",
					},
					{
						"action_id": "assignment_1",
						"action_label": "Set Literal",
						"action_type": "Assignment",
						"config": [
							{
								"target": "doc.first_name",
								"operator": "set",
								"value": {"mode": "static", "value_type": "Data", "value": ""},
								"value_source": "literal",
								"value_literal": "",
							}
						],
					},
				],
			}
		)

		rule.validate()

	def test_compiled_artifact_redis_cache_only(self):
		"""Verify that compiled artifacts are cached in Redis and NOT stored on the Rule document."""
		rule = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": f"Test Redis Cache Rule {frappe.generate_hash(length=6)}",
				"document_type": "User",
				"trigger_type": "DocType Event",
				"trigger_event": "Before Save",
				"actions": [
					{
						"action_id": "stop_success",
						"action_label": "Stop Success",
						"action_type": "Stop",
						"operation": "Success",
					}
				],
			}
		)
		self._insert_with_retry(rule)

		# The document fields should not exist (since they were removed from the doctype)
		self.assertFalse(hasattr(rule, "compiled_artifact"))
		self.assertFalse(hasattr(rule, "compiled_hash"))
		self.assertFalse(hasattr(rule, "compiled_at"))

		# Retrieve from Redis cache via compile_service
		from flexirule.ruleflow.core.compile_service import get_compiled_artifact

		artifact = get_compiled_artifact(rule.name)
		self.assertIsNotNone(artifact)
		assert artifact is not None  # type narrowing for mypy
		self.assertEqual(artifact.get("rule"), rule.name)
		self.assertEqual(artifact.get("artifact_version"), 2)

	def test_rule_dashboard_data_and_counts(self):
		"""Verify that Rule dashboard metadata and get_open_count work as expected."""
		meta = frappe.get_meta("Rule")
		dashboard_data = meta.get_dashboard_data()

		# Verify fieldname and transactions structure
		self.assertEqual(dashboard_data.get("fieldname"), "rule")
		transaction_groups = {
			group["label"]: group["items"] for group in dashboard_data.get("transactions", [])
		}
		self.assertIn("Rule Execution Log", transaction_groups.get("Logs & Schedulers", []))
		self.assertIn("Rule Scheduler", transaction_groups.get("Logs & Schedulers", []))
		self.assertIn("Data Review Task", transaction_groups.get("Tasks", []))
		self.assertIn("Rule", transaction_groups.get("Related Rules", []))

		# Create target sub-rule
		subrule_name = f"Test Sub Rule {frappe.generate_hash(length=6)}"
		subrule = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": subrule_name,
				"trigger_type": "Callable Event",
				"exposed_as_subrule": 1,
				"priority": "0",
				"actions": [{"action_id": "root", "action_label": "Start", "action_type": "Entry Action"}],
			}
		)
		self._insert_with_retry(subrule)

		# Create parent caller rule referencing subrule
		caller_name = f"Test Parent Caller {frappe.generate_hash(length=6)}"
		caller_rule = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": caller_name,
				"document_type": "User",
				"trigger_type": "DocType Event",
				"trigger_event": "Before Save",
				"actions": [
					{
						"action_id": "root",
						"action_label": "Start",
						"action_type": "Entry Action",
						"next_step_if_true": "sub_1",
					},
					{
						"action_id": "sub_1",
						"action_label": "Call Sub",
						"action_type": "Sub-Rule",
						"rule": subrule.name,
					},
				],
			}
		)
		self._insert_with_retry(caller_rule)

		# Call get_open_count for subrule
		from frappe.desk.notifications import get_open_count

		counts = get_open_count("Rule", subrule.name)
		external_found = counts.get("count", {}).get("external_links_found", [])

		# Verify parent rule is counted in external_links_found for Rule
		rule_link_found = next((item for item in external_found if item.get("doctype") == "Rule"), None)
		self.assertIsNotNone(rule_link_found)
		assert rule_link_found is not None
		self.assertEqual(rule_link_found.get("count"), 1)

	def test_assignment_lifecycle_draft_vs_active(self):
		"""Drafts may be incomplete, but incomplete Assignment plans cannot execute or activate."""
		draft_rule = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": "Test Draft Assignment Lifecycle",
				"trigger_type": "DocType Event",
				"document_type": "ToDo",
				"trigger_event": "Before Insert",
				"is_active": 0,
				"actions": [
					{
						"action_id": "assign-lifecycle-1",
						"action_label": "Draft Assignment",
						"action_type": "Assignment",
						"config": "",
					}
				],
			}
		)
		draft_rule.insert(ignore_permissions=True)
		self.assertEqual(draft_rule.is_active, 0)

		# An incomplete Draft is editable, not executable. The runtime plan compiler
		# must reject its empty Assignment config with the same typed error used by
		# the runtime guard instead of silently normalizing it to a no-op.
		from flexirule.ruleflow.core.action_plan_cache import (
			clear_rule_action_plan_cache,
			get_rule_action_plan,
		)
		from flexirule.ruleflow.core.condition_errors import ConditionValidationError

		clear_rule_action_plan_cache(draft_rule.name)
		with self.assertRaises(ConditionValidationError) as raised:
			get_rule_action_plan(draft_rule)
		self.assertEqual(raised.exception.code, "assignment_config_required")

		draft_rule.reload()
		draft_rule.is_active = 1
		with self.assertRaises(frappe.ValidationError):
			draft_rule.save(ignore_permissions=True)

		draft_rule.reload()
		draft_rule.is_active = 1
		for action in draft_rule.actions:
			if action.action_type == "Assignment":
				action.config = json.dumps([{"target": "doc.status", "value": "Closed"}])
		draft_rule.save(ignore_permissions=True)
		self.assertEqual(draft_rule.is_active, 1)
		draft_rule.delete(ignore_permissions=True)
