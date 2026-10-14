"""Regression tests for system-rule foundation and Rule lifecycle hooks."""
import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.doctype.rule.rule import Rule
from flexirule.ruleflow.hooks import get_excluded_doctypes


class TestSystemRuleFoundation(FrappeTestCase):
    def test_before_insert_is_a_rule_controller_hook(self):
        # Frappe discovers controller lifecycle methods from the class, not from
        # nested function definitions inside another method.
        self.assertIn("before_insert", Rule.__dict__)
        self.assertTrue(callable(Rule.__dict__["before_insert"]))

    def test_rule_metadata_has_system_ownership_fields(self):
        meta = frappe.get_meta("Rule")
        self.assertTrue(meta.has_field("is_system_generated"))
        self.assertTrue(meta.has_field("system_rule_version"))

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
