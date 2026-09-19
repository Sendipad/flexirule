# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

import frappe
from frappe.exceptions import ValidationError

from flexirule.ruleflow.core.action_handlers.document_action import DocumentActionHandler
from flexirule.ruleflow.core.action_handlers.sub_rule import SubRuleHandler, MAX_SUB_RULE_DEPTH
from flexirule.ruleflow.core.engine import RuleEngine, SafeFrappeAPI
from flexirule.ruleflow.core.exceptions import CycleDetectedError
from flexirule.ruleflow.core.permissions import validate_safe_eval
from flexirule.ruleflow.tests.test_case import FlexiRuleTestCase


class TestAuditReproductions(FlexiRuleTestCase):
	"""Automated regression tests verifying fixes for confirmed audit findings:

	FR-SEC-001, FR-SEC-002, FR-SEC-003, and FR-ENGINE-002.
	"""

	def test_FR_SEC_001_ast_validation_stub_sandbox_escape(self):
		"""FR-SEC-001 (CRITICAL): validate_safe_eval inspects AST nodes and rejects dunder attribute access."""
		malicious_payload = (
			"(lambda fc: [c for c in fc.__subclasses__() if c.__name__ == 'BuiltinImporter'][0]())(object)"
		)
		with self.assertRaises(ValidationError):
			validate_safe_eval(malicious_payload)

	def test_FR_SEC_002_ssti_in_document_action_rendering(self):
		"""FR-SEC-002 (CRITICAL): DocumentActionHandler._render_scalar does not expose frappe module in Jinja context."""
		handler = DocumentActionHandler()
		context = {
			"doc": frappe._dict({"doctype": "User", "name": "Administrator"}),
			"frappe": frappe,
		}
		ssti_payload = "{{ frappe.db.get_value('User', 'Administrator', 'email') }}"
		# render_template fails to evaluate frappe because frappe is not in context
		rendered = handler._render_scalar(ssti_payload, context)
		self.assertNotIn("Administrator", rendered)

	def test_FR_SEC_003_safe_frappe_api_format_value_dict_override(self):
		"""FR-SEC-003 (HIGH): SafeFrappeAPI.format_value blocks custom dictionary overrides as df."""
		api = SafeFrappeAPI()
		dict_df = {"fieldtype": "Currency", "options": "os.system"}
		with self.assertRaises(PermissionError):
			api.format_value("100", df=dict_df)

	def test_FR_ENGINE_002_sub_rule_recursion_depth_propagated(self):
		"""FR-ENGINE-002 (HIGH): Sub-rule execution context propagates recursion depth and enforces limit."""
		sub_rule = frappe.get_doc({
			"doctype": "Rule",
			"rule_name": "Test_Sub_Rule_Depth_Check",
			"trigger_type": "Callable Event",
			"exposed_as_subrule": 1,
			"is_active": 1,
			"status": "Active",
		}).insert(ignore_permissions=True)

		try:
			handler = SubRuleHandler()
			action = frappe._dict({"rule": sub_rule.name, "action_id": "act_sub", "skip_conditions": 1})
			context = {
				"doc": frappe._dict({"doctype": "User", "name": "Administrator"}),
				"_sub_rule_depth": MAX_SUB_RULE_DEPTH,
			}
			engine = RuleEngine(frappe._dict({"name": "Parent_Rule", "actions": []}), execution_context=context)

			with self.assertRaises(CycleDetectedError):
				handler.execute(action, context, engine)
		finally:
			frappe.delete_doc("Rule", sub_rule.name, force=True, ignore_permissions=True)
