import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.core.coordinator import RuleCoordinator


class FlexiRuleTestCase(FrappeTestCase):
	def execute_rule(self, rule_name, doc, **kwargs):
		"""Helper to execute a rule and return the result payload."""
		RuleCoordinator.execute_rule(rule_name, {"doc": doc, **kwargs})
		# RuleEngine.execute stores the payload in frappe.local.execution_payload
		return getattr(frappe.local, "execution_payload", {})

	def assert_success(self, result):
		self.assertEqual(result.get("status"), "Success", f"Rule failed with errors: {result.get('errors')}")

	def assert_failed(self, result):
		self.assertEqual(result.get("status"), "Failed")

	def assert_rule_executed(self, result, action_label):
		path = [step.get("action") for step in result.get("path_trace", [])]
		self.assertIn(
			action_label, path, f"Action '{action_label}' was not executed. Path: {' -> '.join(path)}"
		)

	def assert_path_executed(self, result, expected_path):
		actual_path = [step.get("action") for step in result.get("path_trace", [])]
		# Check if expected_path is a sub-sequence of actual_path
		# Or simple equality if we expect the FULL path
		self.assertEqual(actual_path, expected_path)

	def assert_document_updated(self, doc, fieldname, expected_value):
		self.assertEqual(doc.get(fieldname), expected_value)

	def assert_variable_set(self, result, var_name, expected_value):
		vars = result.get("vars", {})
		self.assertEqual(vars.get(var_name), expected_value)
