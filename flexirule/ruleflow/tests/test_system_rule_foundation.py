"""Regression tests for system-rule foundation and Rule lifecycle hooks."""
from unittest.mock import patch

import frappe
from flexirule.ruleflow.tests.test_case import FlexiRuleTestCase

from flexirule.ruleflow.doctype.rule.rule import Rule
from flexirule.ruleflow.hooks import get_excluded_doctypes


class TestSystemRuleFoundation(FlexiRuleTestCase):
    def test_before_insert_is_a_rule_controller_hook(self):
        # Frappe discovers controller lifecycle methods from the class, not from
        # nested function definitions inside another method.
        self.assertIn("before_insert", Rule.__dict__)
        self.assertTrue(callable(Rule.__dict__["before_insert"]))

    def test_rule_has_system_ownership_marker_without_custom_source_version(self):
        meta = frappe.get_meta("Rule")
        self.assertTrue(meta.has_field("is_system_generated"))
        self.assertFalse(meta.has_field("system_rule_version"))

    def test_system_rule_ownership_marker_cannot_be_cleared(self):
        rule = frappe.new_doc("Rule")
        rule.rule_name = "test-system-rule"
        rule.is_system_generated = 0
        before = frappe._dict(is_system_generated=1)

        with patch.object(rule, "get_doc_before_save", return_value=before):
            with self.assertRaises(frappe.ValidationError):
                rule.validate_system_rule_protection()

    def test_user_rule_cannot_claim_system_ownership(self):
        rule = frappe.new_doc("Rule")
        rule.rule_name = "test-user-rule"
        rule.is_system_generated = 1
        before = frappe._dict(is_system_generated=0)

        with patch.object(rule, "get_doc_before_save", return_value=before):
            with self.assertRaises(frappe.ValidationError):
                rule.validate_system_rule_protection()

    def test_core_flexirule_doctypes_are_not_hard_excluded(self):
        # Older sites may still have these DocTypes stored in RuleFlow Settings.
        old_local = getattr(frappe.local, "flexirule_excluded_doctypes", None)
        if hasattr(frappe.local, "flexirule_excluded_doctypes"):
            delattr(frappe.local, "flexirule_excluded_doctypes")
        try:
            excluded = get_excluded_doctypes()
            for doctype in (
                "Rule",
                "Rule Action",
                "Process",
                "Process Operation",
                "Data Review Task",
                "Data Review Related Document",
            ):
                self.assertNotIn(doctype, excluded)
        finally:
            if hasattr(frappe.local, "flexirule_excluded_doctypes"):
                delattr(frappe.local, "flexirule_excluded_doctypes")
            if old_local is not None:
                frappe.local.flexirule_excluded_doctypes = old_local
