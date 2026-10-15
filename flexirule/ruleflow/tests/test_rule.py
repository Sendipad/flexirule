# Copyright (c) 2025, FlexiRule and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule import hooks as app_hooks
from flexirule.ruleflow.core.action_handlers import HandlerRegistry
from flexirule.ruleflow.core.coordinator import RuleCoordinator
from flexirule.ruleflow.core.engine import RuleEngine
from flexirule.ruleflow.hooks import execute_rules, execute_rules_from_event, get_excluded_doctypes

# On IntegrationTestCase, the doctype test records and all
# link-field test record depdendencies are recursively loaded
# Use these module variables to add/remove to/from that list
# EXTRA_TEST_RECORD_DEPENDENCIES = ["...]  # eg. ["User"]
# IGNORE_TEST_RECORD_DEPENDENCIES = ["..."]  # eg. ["User"]


class TestRule(FrappeTestCase):
	def tearDown(self):
		super().tearDown()
		frappe.db.delete("Rule", {"rule_name": ["like", "Test Rule Validation%"]})

	def test_active_rule_requires_next_step(self):
		rule = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": "Test Rule Validation Missing False Path",
				"document_type": "ToDo",
				"trigger_type": "DocType Event",
				"trigger_event": "Validate",
				"is_active": 1,
				"actions": [
					{
						"action_id": "root",
						"action_type": "Entry Action",
						"action_label": "Start",
						"next_step_if_true": "condition_1",
					},
					{
						"action_id": "condition_1",
						"action_type": "Condition",
						"action_label": "Check",
						"condition_json": '[{"left":{"ref":"doc.description"},"op":"!=","right":{"value":""}}]',
						"next_step_if_true": "stop_1",
					},
					{
						"action_id": "stop_1",
						"action_type": "Stop",
						"action_label": "Stop",
					},
				],
			}
		)

		with self.assertRaises(frappe.ValidationError):
			rule.insert(ignore_permissions=True)

	def test_update_context_variable_requires_existing_variable(self):
		rule = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": "Test Rule Validation Missing Context Variable",
				"document_type": "ToDo",
				"trigger_type": "DocType Event",
				"trigger_event": "Validate",
				"is_active": 1,
				"actions": [
					{
						"action_id": "root",
						"action_type": "Entry Action",
						"action_label": "Start",
						"next_step_if_true": "action_1",
					},
					{
						"action_id": "action_1",
						"action_type": "Query Records",
						"operation": "Query Doc",
						"reference_doctype": "ToDo",
						"mutation_mode": "Update Context Variable",
						"return_variable": "non_existent_var",
						"next_step_if_true": "stop_1",
					},
					{
						"action_id": "stop_1",
						"action_type": "Stop",
						"action_label": "Stop",
					},
				],
			}
		)

		with self.assertRaises(frappe.ValidationError):
			rule.insert(ignore_permissions=True)

	def test_scheduler_rule_clears_doc_event_fields(self):
		rule = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": "Test Rule Validation Scheduler Leakage",
				"document_type": "ToDo",
				"trigger_type": "Scheduler Event",
				"trigger_event": "Validate",
				"is_active": 0,
				"actions": [],
			}
		)

		rule.insert(ignore_permissions=True)
		self.assertFalse(rule.trigger_event)

	def test_sub_rule_target_must_be_callable_exposed_and_active(self):
		target_rule = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": "Test Rule Validation Hidden Target",
				"document_type": "ToDo",
				"trigger_type": "Callable Event",
				"priority": "0",
				"is_active": 1,
				"exposed_as_subrule": 0,
				"actions": [{"action_id": "root", "action_type": "Entry Action", "action_label": "Start"}],
			}
		).insert(ignore_permissions=True)

		parent_rule = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": "Test Rule Validation Parent",
				"document_type": "ToDo",
				"trigger_type": "Callable Event",
				"priority": "0",
				"is_active": 1,
				"actions": [
					{
						"action_id": "root",
						"action_type": "Entry Action",
						"action_label": "Start",
						"next_step_if_true": "call_sub_rule",
					},
					{
						"action_id": "call_sub_rule",
						"action_type": "Sub-Rule",
						"action_label": "Call Target",
						"rule": target_rule.name,
					},
				],
			}
		)

		with self.assertRaises(frappe.ValidationError):
			parent_rule.insert(ignore_permissions=True)

	def test_notify_email_requires_subject_and_recipients(self):
		rule = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": "Test Rule Validation Notify Email",
				"document_type": "ToDo",
				"trigger_type": "Callable Event",
				"priority": "0",
				"is_active": 0,
				"actions": [
					{
						"action_id": "root",
						"action_type": "Entry Action",
						"action_label": "Start",
						"next_step_if_true": "notify_1",
					},
					{
						"action_id": "notify_1",
						"action_type": "Notify",
						"action_label": "Notify Email",
						"operation": "Email",
						"value_template": "Hello {{ doc.name }}",
						"config": "{}",
					},
				],
			}
		)

		with self.assertRaises(frappe.ValidationError):
			rule.insert(ignore_permissions=True)


class _NotifyEngineStub:
	def __init__(self):
		self.rule = frappe._dict(name="Test Notify Rule")

	def _get_action_config(self, action):
		return RuleEngine._get_action_config(action)

	def _log(self, level, message):
		return None


class TestNotifyActionHandler(FrappeTestCase):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		self.handler = HandlerRegistry.get("Notify")
		self.engine = _NotifyEngineStub()
		self.doc = frappe.get_doc({"doctype": "ToDo", "description": "Notify Test"})
		self.doc.insert(ignore_permissions=True)
		self.context = {"doc": self.doc, "vars": {}}

	def tearDown(self):
		super().tearDown()
		frappe.db.rollback()

	def test_notify_email_uses_configured_subject_and_recipients(self):
		action = frappe._dict(
			{
				"action_label": "Email Users",
				"operation": "Email",
				"value_template": "Hello {{ doc.name }}",
				"config": '{"recipients":"owner@example.com","subject":"Task {{ doc.name }}","attach_doc":0}',
				"next_step_if_true": None,
			}
		)

		with patch("frappe.sendmail") as sendmail:
			assert self.handler is not None
			result, _ = self.handler.execute(action, self.context, self.engine)  # type: ignore

		self.assertEqual(result, "Hello " + self.doc.name)
		sendmail.assert_called_once()
		call_kwargs = sendmail.call_args.kwargs
		self.assertEqual(call_kwargs["recipients"], ["owner@example.com"])
		self.assertEqual(call_kwargs["subject"], f"Task {self.doc.name}")
		self.assertEqual(call_kwargs["message"], f"Hello {self.doc.name}")

	def test_notify_system_notification_creates_notification_log(self):
		action = frappe._dict(
			{
				"action_label": "Notify Owner",
				"operation": "System Notification",
				"value_template": "Please review {{ doc.name }}",
				"config": '{"subject":"Review {{ doc.name }}","for_user":"Administrator"}',
				"next_step_if_true": None,
			}
		)

		assert self.handler is not None
		result, _ = self.handler.execute(action, self.context, self.engine)  # type: ignore

		notification = frappe.get_doc("Notification Log", result)
		self.assertEqual(notification.for_user, "Administrator")
		self.assertEqual(notification.subject, f"Review {self.doc.name}")
		self.assertEqual(notification.email_content, f"Please review {self.doc.name}")

	def test_notify_provider_dispatches_to_hook_registered_provider(self):
		action = frappe._dict(
			{
				"action_label": "Notify Provider",
				"operation": "Provider",
				"value_template": "Provider payload for {{ doc.name }}",
				"config": '{"provider":"slack","recipient":"#ops"}',
				"next_step_if_true": None,
			}
		)

		with (
			patch("frappe.get_installed_apps", return_value=["flexirule"]),
			patch(
				"frappe.get_hooks",
				return_value={"slack": "flexirule.tests.fake_provider.send"},
			),
			patch("frappe.get_attr") as get_attr,
		):
			mock_sender = get_attr.return_value
			mock_sender.return_value = {"sent": True}

			assert self.handler is not None
			result, _ = self.handler.execute(action, self.context, self.engine)  # type: ignore

		self.assertEqual(result, {"sent": True})
		mock_sender.assert_called_once()
		self.assertEqual(mock_sender.call_args.kwargs["recipient"], "#ops")
		self.assertEqual(
			mock_sender.call_args.kwargs["message"],
			f"Provider payload for {self.doc.name}",
		)


class TestRuleDocEventDispatch(FrappeTestCase):
	def tearDown(self):
		for attr in ("flexirule_excluded_doctypes", "flexirule_rule_dispatch_depth"):
			if hasattr(frappe.local, attr):
				delattr(frappe.local, attr)
		if hasattr(frappe.flags, "flexirule_system_rule_registration"):
			delattr(frappe.flags, "flexirule_system_rule_registration")
		super().tearDown()

	def test_internal_doctypes_are_not_implicitly_excluded(self):
		with patch("frappe.get_hooks", return_value=[]), patch("frappe.get_all", return_value=[]):
			excluded = get_excluded_doctypes()

		self.assertNotIn("Rule", excluded)
		self.assertNotIn("Process", excluded)
		self.assertIn("Rule Scheduler", excluded)
		self.assertIn("Rule Execution Log", excluded)

	def test_configured_exclusions_are_preserved_except_legacy_rule_default(self):
		def get_all(doctype, **kwargs):
			if doctype == "RuleFlow Excluded DocType":
				return ["Rule", "Rule Scheduler", "Process"]
			return []

		with patch("frappe.get_hooks", return_value=[]), patch("frappe.get_all", side_effect=get_all):
			excluded = get_excluded_doctypes()

		# Rule was seeded by older versions as a default exclusion; it is now an
		# event target. Other settings exclusions remain authoritative.
		self.assertNotIn("Rule", excluded)
		self.assertIn("Process", excluded)
		self.assertIn("Rule Scheduler", excluded)
		self.assertIn("Rule Execution Log", excluded)

	def test_app_hook_can_explicitly_exclude_rule(self):
		with (
			patch("frappe.get_hooks", return_value=["Rule"]),
			patch("frappe.get_all", return_value=["Rule"]),
		):
			excluded = get_excluded_doctypes()

		self.assertIn("Rule", excluded)

	def test_rule_document_event_is_dispatched(self):
		doc = frappe._dict(doctype="Rule", name="RULE_EVENT_TEST")
		with (
			patch("flexirule.ruleflow.core.coordinator.RuleCoordinator.has_active_rules", return_value=True),
			patch("flexirule.ruleflow.core.coordinator.RuleCoordinator.execute_rules_from_event") as execute,
			patch("frappe.get_hooks", return_value=[]),
			patch("frappe.get_all", return_value=[]),
		):
			if hasattr(frappe.local, "flexirule_excluded_doctypes"):
				delattr(frappe.local, "flexirule_excluded_doctypes")
			execute_rules_from_event(doc, "After Save")

		execute.assert_called_once_with(doc, "After Save")

	def test_child_and_single_doctypes_are_rejected_as_rule_targets(self):
		rule = frappe.new_doc("Rule")
		rule.trigger_type = "DocType Event"

		for doctype in ("Rule Action", "RuleFlow Settings"):
			rule.document_type = doctype
			with self.subTest(doctype=doctype), self.assertRaises(frappe.ValidationError):
				rule.validate_document_event_target()

	def test_rule_registry_is_invalidated_after_rule_deletion(self):
		doc = frappe._dict(doctype="Rule", name="RULE_DELETED_TEST")
		self.assertTrue(RuleCoordinator.should_rebuild_registry_for_rule_change(doc, "after_delete"))

	def test_rule_cache_invalidation_uses_doctype_specific_hooks(self):
		rule_hooks = app_hooks.doc_events["Rule"]
		clear_cache = "flexirule.ruleflow.hooks.clear_rule_cache"
		for method in ("after_insert", "on_update", "on_trash", "after_delete"):
			self.assertEqual(rule_hooks[method], clear_cache)

		# Event dispatch remains the wildcard hook, separate from invalidation.
		self.assertEqual(
			app_hooks.doc_events["*"]["on_update"],
			"flexirule.ruleflow.hooks.execute_rules",
		)

	def test_generic_dispatch_does_not_clear_rule_cache_itself(self):
		doc = frappe._dict(doctype="Rule", name="RULE_CACHE_TEST")
		with (
			patch("flexirule.ruleflow.hooks.clear_rule_cache") as clear_cache,
			patch("flexirule.ruleflow.hooks.execute_rules_from_event") as dispatch,
		):
			execute_rules(doc, "on_update")

		clear_cache.assert_not_called()
		dispatch.assert_called_once_with(doc, "After Save")

	def test_system_rule_registration_flag_suppresses_dispatch(self):
		doc = frappe._dict(doctype="Rule", name="SYSTEM_RULE_REGISTRATION_TEST")
		frappe.flags.flexirule_system_rule_registration = True
		with patch("flexirule.ruleflow.core.coordinator.RuleCoordinator.has_active_rules") as has_rules:
			execute_rules_from_event(doc, "After Save")
		has_rules.assert_not_called()

	def test_indirect_rule_dispatch_depth_is_bounded_and_restored(self):
		def dispatch_next(doc, event):
			next_doctype = "DocType B" if doc.doctype == "DocType A" else "DocType A"
			execute_rules_from_event(frappe._dict(doctype=next_doctype, name="RECURSION_TEST"), event)

		doc = frappe._dict(doctype="DocType A", name="RECURSION_TEST")
		with (
			patch("flexirule.ruleflow.core.coordinator.RuleCoordinator.has_active_rules", return_value=True),
			patch(
				"flexirule.ruleflow.core.coordinator.RuleCoordinator.execute_rules_from_event",
				side_effect=dispatch_next,
			),
			patch("frappe.get_hooks", return_value=[]),
			patch("frappe.get_all", return_value=[]),
			self.assertRaises(frappe.ValidationError),
		):
			if hasattr(frappe.local, "flexirule_excluded_doctypes"):
				delattr(frappe.local, "flexirule_excluded_doctypes")
			execute_rules_from_event(doc, "After Save")

		self.assertEqual(getattr(frappe.local, "flexirule_rule_dispatch_depth", None), 0)
