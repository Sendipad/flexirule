"""
Hook wrapper functions for FlexiRule rule engine.
These are called from hooks.py doc_events.
"""

from __future__ import annotations

import frappe

EVENT_MAP = {
	"before_naming": "Before Naming",
	"before_insert": "Before Insert",
	"before_save": "Before Save",
	"validate": "Validate",
	"after_insert": "After Insert",
	"on_update": "After Save",
	"before_submit": "Before Submit",
	"on_submit": "On Submit",
	"on_update_after_submit": "On Update After Submit",
	"on_change": "On Change",
	"before_cancel": "Before Cancel",
	"on_cancel": "On Cancel",
	"on_trash": "On Trash",
	"before_print": "Before Print",
	"before_rename": "Before Rename",
	"after_rename": "After Rename",
}


# Request-level memo key for excluded doctypes
EXCLUDED_CACHE_KEY = "flexirule_excluded_doctypes"


def get_excluded_doctypes() -> set[str]:
	"""Get list of doctypes excluded from lifecycle dispatch (request-memoized)."""
	cached = getattr(frappe.local, EXCLUDED_CACHE_KEY, None)
	if isinstance(cached, set):
		return cached

	excluded = set(frappe.get_hooks("flexirule_excluded_doctypes") or [])
	excluded.update(
		{
			"Error Log",
			"Activity Log",
			"Access Log",
			"Email Queue",
			"Scheduled Job Log",
			"Version",
			"Comment",
			"Communication",
			"File",
			# Engine telemetry stays excluded to avoid rules firing from their own
			# execution bookkeeping.
			"Rule Execution Log",
			"Rule Scheduler",
		}
	)

	try:
		user_excluded = frappe.get_all(
			"RuleFlow Excluded DocType", parent="RuleFlow Settings", pluck="document_type"
		)
		if user_excluded:
			excluded.update([dt for dt in user_excluded if dt])
		# FlexiRule definition/configuration DocTypes are eligible rule targets even
		# if older installations seeded them into the excluded list.
		excluded.difference_update(
			{
				"Rule",
				"Rule Action",
				"Process",
				"Process Operation",
				"Data Review Task",
				"Data Review Related Document",
			}
		)
	except Exception:
		# Table might not exist yet during install/migrate.
		pass

	setattr(frappe.local, EXCLUDED_CACHE_KEY, excluded)
	return excluded


def execute_rules(doc, method=None, *args, **kwargs):
	"""Standard Frappe doc_event hook entry point."""
	trigger_event = EVENT_MAP.get(method)
	if not trigger_event:
		return

	return execute_rules_from_event(doc, trigger_event)


def execute_rules_from_event(doc, event):
	"""Pure hook logic decoupled from Frappe method names."""
	if frappe.flags.in_import or frappe.flags.in_migrate:
		return

	if getattr(frappe.flags, "flexirule_system_rule_registration", False):
		return

	if doc.doctype in get_excluded_doctypes():
		return

	from flexirule.ruleflow.core.coordinator import RuleCoordinator

	# Compiled runtime registry provides negative caching and fast no-rule exits.
	if not RuleCoordinator.has_active_rules(doc.doctype, event):
		return

	# The coordinator protects same-document/event re-entry. Bound nested events too,
	# so indirect A -> B -> A write cycles cannot recurse without limit.
	depth = getattr(frappe.local, "flexirule_rule_dispatch_depth", 0)
	max_depth = 20
	if depth >= max_depth:
		frappe.throw(f"FlexiRule stopped a recursive rule chain after {max_depth} nested document events.")

	frappe.local.flexirule_rule_dispatch_depth = depth + 1
	try:
		RuleCoordinator.execute_rules_from_event(doc, event)
	finally:
		frappe.local.flexirule_rule_dispatch_depth = depth


def get_flexirule_map():
	"""Backward-compatible helper to fetch doctype/event rule map."""
	from flexirule.ruleflow.core.coordinator import RuleCoordinator

	return RuleCoordinator.get_rule_map()


def clear_rule_cache(doc=None, method=None, *args, **kwargs):
	"""Selective runtime-registry invalidation for Rule lifecycle changes."""
	from flexirule.ruleflow.core.action_plan_cache import clear_rule_action_plan_cache
	from flexirule.ruleflow.core.compile_service import clear_compiled_artifact_cache
	from flexirule.ruleflow.core.coordinator import RuleCoordinator

	if not doc:
		clear_rule_action_plan_cache()
		clear_compiled_artifact_cache()
		RuleCoordinator.clear_cache()
		return

	if RuleCoordinator.should_rebuild_registry_for_rule_change(doc, method):
		clear_rule_action_plan_cache(rule_name=doc.name)
		clear_compiled_artifact_cache(rule_name=doc.name)
		RuleCoordinator.clear_cache(doctype=doc.get("document_type"))
