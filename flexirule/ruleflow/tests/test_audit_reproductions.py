# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

import unittest
import frappe

from flexirule.ruleflow.core.engine import SafeFrappeAPI, RuleEngine
from flexirule.ruleflow.core.permissions import validate_safe_eval
from flexirule.ruleflow.core.action_handlers.document_action import DocumentActionHandler
from flexirule.ruleflow.tests.test_case import FlexiRuleTestCase


class TestAuditReproductions(FlexiRuleTestCase):
	"""
	Automated regression tests reproducing key bugs confirmed during the full repository audit.
	These tests serve as deterministic evidence for findings FR-SEC-001, FR-SEC-002, FR-SEC-003,
	and FR-ENGINE-002.
	"""

	@unittest.expectedFailure
	def test_FR_SEC_001_ast_validation_stub_sandbox_escape(self):
		"""
		FR-SEC-001 (CRITICAL): validate_safe_eval only compiles syntax without inspecting AST nodes.
		Expected failure: The function should raise ValidationError for dunder attributes/subclasses,
		but currently returns True because it is a syntax-only stub.
		"""
		malicious_payload = "(lambda fc: [c for c in fc.__subclasses__() if c.__name__ == 'BuiltinImporter'][0]())(object)"
		# Currently passes compile() without raising ValidationError
		result = validate_safe_eval(malicious_payload)
		# This assertion fails because validate_safe_eval returned True instead of throwing ValidationError
		self.assertFalse(result, "validate_safe_eval should reject dunder attribute traversal")

	@unittest.expectedFailure
	def test_FR_SEC_002_ssti_in_document_action_rendering(self):
		"""
		FR-SEC-002 (CRITICAL): DocumentActionHandler._render_scalar passes unfiltered template
		context with global frappe module into frappe.render_template.
		Expected failure: Rendered output should sanitize SQL or block frappe module access,
		but currently executes the template statement.
		"""
		handler = DocumentActionHandler()
		context = {
			"doc": frappe._dict({"doctype": "User", "name": "Administrator"}),
			"frappe": frappe,
		}
		ssti_payload = "{{ frappe.db.get_value('User', 'Administrator', 'email') }}"
		rendered = handler._render_scalar(ssti_payload, context)
		# Should not evaluate raw frappe calls inside render_scalar
		self.assertEqual(rendered, ssti_payload, "render_scalar should not execute raw frappe DB queries")

	@unittest.expectedFailure
	def test_FR_SEC_003_safe_frappe_api_format_value_dict_override(self):
		"""
		FR-SEC-003 (HIGH): SafeFrappeAPI.format_value accepts unvalidated dict overrides as df,
		allowing dynamic formatter execution.
		Expected failure: Should throw TypeError or PermissionError for non-DocField objects,
		but currently delegates directly to frappe.format_value.
		"""
		api = SafeFrappeAPI()
		dict_df = {"fieldtype": "Currency", "options": "os.system"}
		with self.assertRaises(PermissionError):
			api.format_value("100", df=dict_df)

	def test_FR_ENGINE_002_sub_rule_recursion_depth_not_checked_in_validate(self):
		"""
		FR-ENGINE-002 (HIGH): Sub-rule execution context does not propagate depth or check depth limit
		in engine initialization, demonstrating that MAX_SUB_RULE_DEPTH = 2 is unenforced.
		"""
		context = {"_sub_rule_depth": 3}
		rule = frappe._dict({"name": "Test_Rule", "actions": [frappe._dict({"action_type": "Stop", "is_enabled": 1})], "is_active": 1})
		engine = RuleEngine(rule, execution_context=context)
		# _validate_execution does not throw error despite depth > 2
		engine._validate_execution()
		self.assertEqual(engine.context.get("_sub_rule_depth"), 3)
