"""Regression tests for system-rule registration and Rule lifecycle hooks."""

from unittest.mock import patch

import frappe

from flexirule.ruleflow.core.system_rule_registry import (
	ensure_system_rule,
	ensure_system_rules,
	register_configured_system_rules,
)
from flexirule.ruleflow.doctype.rule.rule import Rule
from flexirule.ruleflow.hooks import execute_rules_from_event, get_excluded_doctypes
from flexirule.ruleflow.tests.test_case import FlexiRuleTestCase
from flexirule.ruleflow.tests.test_doctypes import setup_test_doctypes


class TestSystemRuleFoundation(FlexiRuleTestCase):
	def _patch_frappe_flags(self, **updates):
		"""Patch flags through the Frappe module even when no request-local flags exist."""
		flags = frappe._dict(getattr(frappe, "flags", None) or {})
		flags.update(updates)
		return patch.object(frappe, "flags", flags)

	def _system_definition(self, rule_name, description="Managed definition"):
		"""Build a realistic, versioned callable Rule definition for registry tests."""
		setup_test_doctypes()
		return {
			"rule_name": rule_name,
			"description": description,
			"module": "Ruleflow",
			"document_type": "Test Contact",
			"trigger_type": "Callable Event",
			"trigger_event": None,
			"exposed_as_subrule": 1,
			"priority": "0",
			"max_execution_time": 30,
			"is_active": 1,
			"status": "Active",
			"actions": [
				{
					"action_id": "root",
					"action_type": "Entry Action",
					"action_label": "Start",
					"is_enabled": 1,
					"next_step_if_true": "stop_node",
				},
				{
					"action_id": "stop_node",
					"action_type": "Stop",
					"action_label": "Stop",
					"is_enabled": 1,
					"operation": "Success",
				},
			],
		}

	def _activate(self, rule_name):
		rule = frappe.get_doc("Rule", rule_name)
		rule.is_active = 1
		rule.save(ignore_permissions=True)
		return frappe.get_doc("Rule", rule_name)

	def _create_active_rule_event_probe(self, rule_name):
		from flexirule.ruleflow.core.coordinator import RuleCoordinator
		from flexirule.ruleflow.tests.builder import RuleBuilder

		event_rule = (
			RuleBuilder(rule_name)
			.replace_existing(False)
			.document_type("Rule")
			.trigger("DocType Event", "After Save")
			.active(0)
			.entry_action(next_step="stop_node")
			.stop(action_id="stop_node")
			.build()
		)
		frappe.db.set_value(
			"Rule",
			event_rule.name,
			{"is_active": 1, "status": "Active"},
			update_modified=False,
		)
		RuleCoordinator.clear_cache()
		return event_rule

	def test_before_insert_is_a_rule_controller_hook(self):
		# Frappe discovers controller lifecycle methods from the class, not from
		# nested function definitions inside another method.
		self.assertIn("before_insert", Rule.__dict__)
		self.assertTrue(callable(Rule.__dict__["before_insert"]))

	def test_rule_has_system_ownership_marker_without_custom_source_version(self):
		meta = frappe.get_meta("Rule")
		self.assertTrue(meta.has_field("is_system_generated"))
		self.assertFalse(meta.has_field("system_rule_version"))

	def test_first_registration_is_draft_and_repeat_registration_is_a_noop(self):
		definition = self._system_definition("SYSTEM_RULE_REGISTRY_TEST")
		definition_name = ensure_system_rule(definition)

		rule = frappe.get_doc("Rule", definition_name)
		self.assertTrue(rule.is_system_generated)
		self.assertEqual(rule.status, "Draft")
		self.assertFalse(rule.is_active)
		modified = rule.modified

		self.assertEqual(ensure_system_rule(definition), definition_name)
		rule.reload()
		self.assertEqual(rule.modified, modified)
		self.assertEqual(rule.status, "Draft")
		self.assertFalse(rule.is_active)

	def test_unchanged_active_system_rule_is_not_saved_again(self):
		definition = self._system_definition("SYSTEM_RULE_ACTIVE_NOOP")
		rule_name = ensure_system_rule(definition)
		rule = self._activate(rule_name)
		modified = rule.modified

		self.assertEqual(ensure_system_rule(definition), rule_name)
		rule.reload()
		self.assertTrue(rule.is_active)
		self.assertEqual(rule.modified, modified)

	def test_source_change_amends_active_system_rule_without_mutating_it(self):
		definition = self._system_definition("SYSTEM_RULE_ACTIVE_AMEND")
		old_name = ensure_system_rule(definition)
		old_rule = self._activate(old_name)
		old_description = old_rule.description

		updated = self._system_definition("SYSTEM_RULE_ACTIVE_AMEND", "Updated source definition")
		new_name = ensure_system_rule(updated)
		old_rule.reload()
		new_rule = frappe.get_doc("Rule", new_name)

		self.assertNotEqual(new_name, old_name)
		self.assertEqual(old_rule.description, old_description)
		self.assertTrue(old_rule.is_active)
		self.assertEqual(old_rule.status, "Active")
		self.assertEqual(new_rule.previous_version, old_name)
		self.assertEqual(new_rule.base_rule_name, "SYSTEM_RULE_ACTIVE_AMEND")
		self.assertEqual(new_rule.version, 2)
		self.assertTrue(new_rule.is_system_generated)
		self.assertFalse(new_rule.is_active)
		self.assertEqual(new_rule.status, "Draft")
		self.assertEqual(new_rule.description, "Updated source definition")

	def test_disabled_system_rule_stays_disabled_during_noop_sync(self):
		definition = self._system_definition("SYSTEM_RULE_DISABLED_SYNC")
		rule_name = ensure_system_rule(definition)
		frappe.db.set_value(
			"Rule",
			rule_name,
			{"is_active": 0, "status": "Disabled"},
			update_modified=False,
		)

		self.assertEqual(ensure_system_rule(definition), rule_name)
		rule = frappe.get_doc("Rule", rule_name)
		self.assertFalse(rule.is_active)
		self.assertEqual(rule.status, "Disabled")

	def test_changed_disabled_system_rule_gets_a_draft_amendment(self):
		definition = self._system_definition("SYSTEM_RULE_DISABLED_AMEND")
		old_name = ensure_system_rule(definition)
		frappe.db.set_value(
			"Rule",
			old_name,
			{"is_active": 0, "status": "Disabled"},
			update_modified=False,
		)

		updated = self._system_definition("SYSTEM_RULE_DISABLED_AMEND", "Updated disabled definition")
		new_name = ensure_system_rule(updated)
		old_rule = frappe.get_doc("Rule", old_name)
		new_rule = frappe.get_doc("Rule", new_name)

		self.assertNotEqual(new_name, old_name)
		self.assertFalse(old_rule.is_active)
		self.assertEqual(old_rule.status, "Disabled")
		self.assertFalse(new_rule.is_active)
		self.assertEqual(new_rule.status, "Draft")
		self.assertEqual(new_rule.previous_version, old_name)

	def test_registry_rejects_user_managed_name_conflict_through_document_save(self):
		definition = self._system_definition("SYSTEM_RULE_NAME_CONFLICT")
		user_definition = dict(definition)
		user_definition["is_active"] = 0
		user_definition["status"] = "Draft"
		user_rule = frappe.get_doc({"doctype": "Rule", **user_definition})
		user_rule.insert(ignore_permissions=True)

		with self.assertRaises(frappe.ValidationError) as cm:
			ensure_system_rule(definition)

		self.assertIn("user-managed Rule already uses that name", str(cm.exception))
		self.assertFalse(frappe.db.get_value("Rule", user_rule.name, "is_system_generated"))

	def test_registry_rejects_unknown_child_fields_before_writing(self):
		definition = self._system_definition("SYSTEM_RULE_INVALID_CHILD_FIELD")
		definition["actions"][0]["unknown_provider_field"] = "must be rejected"

		with self.assertRaises(frappe.ValidationError) as cm:
			ensure_system_rule(definition)

		self.assertIn("unknown_provider_field", str(cm.exception))
		self.assertFalse(frappe.db.exists("Rule", {"rule_name": "SYSTEM_RULE_INVALID_CHILD_FIELD"}))

	def test_registry_rejects_duplicate_logical_names_in_one_batch(self):
		first = self._system_definition("SYSTEM_RULE_DUPLICATE_IDENTITY")
		second = self._system_definition("system_rule_duplicate_identity", "Conflicting provider")

		with self.assertRaises(frappe.ValidationError) as cm:
			ensure_system_rules([first, second])

		self.assertIn("same logical name", str(cm.exception))
		self.assertFalse(frappe.db.exists("Rule", {"rule_name": first["rule_name"]}))

	def test_registry_batch_rolls_back_prior_documents_when_later_definition_fails(self):
		first = self._system_definition("SYSTEM_RULE_BATCH_ROLLBACK")
		invalid = self._system_definition("SYSTEM_RULE_BATCH_ROLLBACK_INVALID")
		invalid["trigger_type"] = "Not A Trigger Type"
		previous_flag = getattr(frappe.flags, "flexirule_system_rule_registration", False)

		with self.assertRaises(frappe.ValidationError):
			ensure_system_rules([first, invalid])

		self.assertFalse(frappe.db.exists("Rule", {"rule_name": "SYSTEM_RULE_BATCH_ROLLBACK"}))
		self.assertFalse(frappe.db.exists("Rule", {"rule_name": "SYSTEM_RULE_BATCH_ROLLBACK_INVALID"}))
		self.assertEqual(
			getattr(frappe.flags, "flexirule_system_rule_registration", False),
			previous_flag,
		)

	def test_configured_provider_hook_registers_rules(self):
		definition = self._system_definition("SYSTEM_RULE_PROVIDER_TEST")
		original_get_hooks = frappe.get_hooks
		original_get_attr = frappe.get_attr

		def get_hooks(hook_name):
			if hook_name == "flexirule_system_rules":
				return ["tests.provider.system_rule_definitions"]
			return original_get_hooks(hook_name)

		def get_attr(path):
			if path == "tests.provider.system_rule_definitions":
				return lambda: [definition]
			return original_get_attr(path)

		with (
			patch.object(frappe, "get_hooks", side_effect=get_hooks),
			patch.object(frappe, "get_attr", side_effect=get_attr),
		):
			names = register_configured_system_rules()

		self.assertEqual(len(names), 1)
		self.assertTrue(frappe.db.get_value("Rule", names[0], "is_system_generated"))

	def test_system_rule_definition_is_protected_through_document_save(self):
		rule_name = ensure_system_rule(self._system_definition("SYSTEM_RULE_SAVE_PROTECTION"))
		rule = frappe.get_doc("Rule", rule_name)
		original_description = rule.description
		rule.description = "Manual edit"

		with self.assertRaises(frappe.ValidationError):
			rule.save(ignore_permissions=True)

		self.assertEqual(
			frappe.db.get_value("Rule", rule_name, "description"),
			original_description,
		)

	def test_system_rule_action_definition_is_protected_through_document_save(self):
		rule_name = ensure_system_rule(self._system_definition("SYSTEM_RULE_ACTION_PROTECTION"))
		rule = frappe.get_doc("Rule", rule_name)
		original_label = rule.actions[0].action_label
		rule.actions[0].action_label = "Manual action edit"

		with self.assertRaises(frappe.ValidationError):
			rule.save(ignore_permissions=True)

		rule.reload()
		self.assertEqual(rule.actions[0].action_label, original_label)

	def test_system_rule_rename_is_blocked_through_frappe_api(self):
		rule_name = ensure_system_rule(self._system_definition("SYSTEM_RULE_RENAME_PROTECTION"))

		with self.assertRaises(frappe.ValidationError):
			frappe.rename_doc("Rule", rule_name, f"{rule_name}_RENAMED")

		self.assertTrue(frappe.db.exists("Rule", rule_name))

	def test_system_rule_delete_is_blocked_through_document_delete(self):
		rule_name = ensure_system_rule(self._system_definition("SYSTEM_RULE_DELETE_PROTECTION"))

		with self.assertRaises(frappe.ValidationError):
			frappe.delete_doc("Rule", rule_name, force=True)

		self.assertTrue(frappe.db.exists("Rule", rule_name))

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

	def test_system_rule_definition_fields_are_protected(self):
		rule = frappe.new_doc("Rule")
		rule.rule_name = "test-system-rule"
		rule.is_system_generated = 1
		rule.description = "Original description"
		before = frappe._dict(
			{field.fieldname: rule.get(field.fieldname) for field in rule.meta.fields if field.fieldname}
		)
		rule.description = "Modified description"

		with patch.object(rule, "get_doc_before_save", return_value=before):
			with self.assertRaises(frappe.ValidationError):
				rule.validate_system_rule_protection()

	def test_system_rule_activation_state_remains_operator_controlled(self):
		rule = frappe.new_doc("Rule")
		rule.rule_name = "test-system-rule"
		rule.is_system_generated = 1
		rule.is_active = 0
		rule.status = "Disabled"
		before = frappe._dict(
			{field.fieldname: rule.get(field.fieldname) for field in rule.meta.fields if field.fieldname}
		)
		rule.is_active = 1
		rule.status = "Active"
		with patch.object(rule, "get_doc_before_save", return_value=before):
			rule.validate_system_rule_protection()

	def test_registry_flag_allows_source_definition_updates(self):
		rule = frappe.new_doc("Rule")
		rule.rule_name = "test-system-rule"
		rule.is_system_generated = 1
		rule.description = "New source definition"
		before = frappe._dict(
			is_system_generated=1,
			rule_name="test-system-rule",
			description="Original description",
			is_active=0,
			status="Disabled",
		)
		with patch.object(rule, "get_doc_before_save", return_value=before):
			with patch.object(frappe, "flags", frappe._dict(flexirule_system_rule_registration=True)):
				rule.validate_system_rule_protection()

	def test_builtin_governance_and_naming_rules_use_trigger_conditions(self):
		from flexirule.ruleflow.core.compiler import ConditionCompiler
		from flexirule.ruleflow.core.coordinator import RuleCoordinator
		from flexirule.ruleflow.system_rules import get_system_rule_definitions

		definitions = {definition["rule_name"]: definition for definition in get_system_rule_definitions()}
		naming = definitions["RULE_NAMING_REJECT_EMPTY_OR_PLACEHOLDER"]
		governance = definitions["RULE_GOVERNANCE_REQUIRE_DESCRIPTION"]
		compiler = ConditionCompiler()
		naming_expression = compiler.compile(naming["trigger_condition"])
		governance_expression = compiler.compile(governance["trigger_condition"])

		self.assertIn("vars.get('is_install')", naming_expression)
		self.assertIn("startswith", naming_expression)
		self.assertIn("is_not_set", naming["trigger_condition"])
		self.assertIn("vars.get('is_install')", governance_expression)

		naming_rule = frappe._dict(
			name=naming["rule_name"],
			is_active=1,
			trigger_type="DocType Event",
			document_type="Rule",
			trigger_event="Before Naming",
			trigger_condition=naming["trigger_condition"],
			compiled_expression=naming_expression,
		)

		# Empty and placeholder names should enter the RuleFlow policy; valid names skip it.
		for rule_name in ("", "new Rule", "NEW_RULE"):
			naming_doc = frappe._dict(doctype="Rule", rule_name=rule_name)
			with self._patch_frappe_flags(in_install=False):
				eligible, reason = RuleCoordinator.check_eligibility(
					naming_rule, naming_doc, "Before Naming"
				)
			self.assertTrue(eligible, f"{rule_name!r} should match the naming policy: {reason}")

		for rule_name in ("Customer Rule", "RULE_CUSTOMER_SYNC"):
			naming_doc = frappe._dict(doctype="Rule", rule_name=rule_name)
			with self._patch_frappe_flags(in_install=False):
				eligible, reason = RuleCoordinator.check_eligibility(
					naming_rule, naming_doc, "Before Naming"
				)
			self.assertFalse(eligible, f"{rule_name!r} should skip the naming policy: {reason}")

		naming_doc = frappe._dict(doctype="Rule", rule_name="new Rule")
		with self._patch_frappe_flags(in_install=True):
			eligible, reason = RuleCoordinator.check_eligibility(
				naming_rule, naming_doc, "Before Naming"
			)
		self.assertFalse(eligible, f"Installation must bypass naming policy: {reason}")

		governance_rule = frappe._dict(
			name=governance["rule_name"],
			is_active=1,
			trigger_type="DocType Event",
			document_type="Rule",
			trigger_event="Before Insert",
			trigger_condition=governance["trigger_condition"],
			compiled_expression=governance_expression,
		)
		governance_doc = frappe._dict(doctype="Rule", description="")
		with self._patch_frappe_flags(in_install=True):
			eligible, reason = RuleCoordinator.check_eligibility(
				governance_rule, governance_doc, "Before Insert"
			)
		self.assertFalse(eligible, reason)

		with self._patch_frappe_flags(in_install=False):
			eligible, reason = RuleCoordinator.check_eligibility(
				governance_rule, governance_doc, "Before Insert"
			)
		self.assertTrue(eligible, reason)

	def test_builtin_system_rules_register_as_inactive_drafts(self):
		names = register_configured_system_rules()

		self.assertIn("RULE_NAMING_REJECT_EMPTY_OR_PLACEHOLDER", names)
		self.assertIn("RULE_GOVERNANCE_REQUIRE_DESCRIPTION", names)
		for name in (
			"RULE_NAMING_NO_OUTER_WHITESPACE",
			"RULE_GOVERNANCE_REQUIRE_DESCRIPTION",
		):
			rule = frappe.get_doc("Rule", name)
			self.assertTrue(rule.is_system_generated)
			self.assertEqual(rule.status, "Draft")
			self.assertFalse(rule.is_active)

	def test_rule_is_removed_from_legacy_settings_exclusions(self):
		from flexirule.install import setup_default_ruleflow_settings

		settings = frappe.get_doc("RuleFlow Settings")
		if not any(row.document_type == "Rule" for row in settings.excluded_doctypes):
			settings.append("excluded_doctypes", {"document_type": "Rule"})
		with self._patch_frappe_flags(in_migrate=True):
			settings.save(ignore_permissions=True)

		setup_default_ruleflow_settings()

		settings.reload()
		self.assertNotIn("Rule", [row.document_type for row in settings.excluded_doctypes])

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

	def test_frappe_save_dispatches_rules_for_internal_rule_doctype(self):
		from flexirule.ruleflow.core.coordinator import RuleCoordinator
		from flexirule.ruleflow.tests.builder import RuleBuilder

		self._create_active_rule_event_probe("SYSTEM_RULE_INTERNAL_EVENT_DISPATCH")
		original_execute = RuleCoordinator.execute_rules_from_event
		dispatched_rule_names = []

		def spy_execute(doc, event_name):
			if doc.doctype == "Rule" and event_name == "After Save":
				dispatched_rule_names.append(doc.name)
			return original_execute(doc, event_name)

		with patch.object(RuleCoordinator, "execute_rules_from_event", new=staticmethod(spy_execute)):
			target = (
				RuleBuilder("SYSTEM_RULE_INTERNAL_EVENT_TARGET")
				.replace_existing(False)
				.document_type("Test Contact")
				.active(0)
				.entry_action(next_step="stop_node")
				.stop(action_id="stop_node")
				.build()
			)

		self.assertIn(target.name, dispatched_rule_names)

	def test_system_rule_registration_suppresses_internal_lifecycle_dispatch(self):
		from flexirule.ruleflow.core.coordinator import RuleCoordinator

		self._create_active_rule_event_probe("SYSTEM_RULE_REGISTRATION_SUPPRESSION_PROBE")
		original_execute = RuleCoordinator.execute_rules_from_event
		dispatched_rule_names = []
		previous_flag = getattr(frappe.flags, "flexirule_system_rule_registration", False)

		def spy_execute(doc, event_name):
			if doc.doctype == "Rule" and event_name == "After Save":
				dispatched_rule_names.append(doc.name)
			return original_execute(doc, event_name)

		with patch.object(RuleCoordinator, "execute_rules_from_event", new=staticmethod(spy_execute)):
			rule_name = ensure_system_rule(
				self._system_definition("SYSTEM_RULE_REGISTRATION_SUPPRESSION_TARGET")
			)

		self.assertNotIn(rule_name, dispatched_rule_names)
		self.assertEqual(
			getattr(frappe.flags, "flexirule_system_rule_registration", False),
			previous_flag,
		)

	def test_indirect_cross_document_rule_dispatch_recursion_is_bounded_and_unwinds(self):
		from flexirule.ruleflow.core.coordinator import RuleCoordinator

		doc = frappe._dict(doctype="Test Contact")
		initial_depth = getattr(frappe.local, "flexirule_rule_dispatch_depth", 0)
		dispatched_events = []

		def dispatch_nested_event(nested_doc, event_name):
			dispatched_events.append((nested_doc.doctype, event_name))
			next_doctype = "Process" if nested_doc.doctype == "Rule" else "Rule"
			next_event = "Before Save" if next_doctype == "Process" else "After Save"
			execute_rules_from_event(frappe._dict(doctype=next_doctype), next_event)

		with (
			patch.object(RuleCoordinator, "has_active_rules", return_value=True),
			patch.object(RuleCoordinator, "execute_rules_from_event", side_effect=dispatch_nested_event),
		):
			with self.assertRaises(frappe.ValidationError) as cm:
				execute_rules_from_event(doc, "Before Save")

		self.assertIn("recursive rule chain", str(cm.exception))
		self.assertTrue({"Rule", "Process"}.issubset({doctype for doctype, _ in dispatched_events}))
		self.assertEqual(
			getattr(frappe.local, "flexirule_rule_dispatch_depth", 0),
			initial_depth,
		)
