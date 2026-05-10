"""
Hook wrapper functions for Bolton rule engine.
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
			# FlexiRule internal doctypes
			"Rule",
			"Rule Action",
			"Rule Execution Log",
			"Rule Scheduler",
			"Process",
			"Process Operation",
			"Data Review Task",
			"Data Review Related Document",
		}
	)

	try:
		user_excluded = frappe.get_all(
			"RuleFlow Excluded DocType", parent="RuleFlow Settings", pluck="document_type"
		)
		if user_excluded:
			excluded.update([dt for dt in user_excluded if dt])
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

	if doc.doctype in get_excluded_doctypes():
		return

	from flexirule.ruleflow.core.coordinator import RuleCoordinator

	# Compiled runtime registry provides negative caching and fast no-rule exits.
	if not RuleCoordinator.has_active_rules(doc.doctype, event):
		return

	RuleCoordinator.execute_rules_from_event(doc, event)


def get_flexirule_map():
	"""Backward-compatible helper to fetch doctype/event rule map."""
	from flexirule.ruleflow.core.coordinator import RuleCoordinator

	return RuleCoordinator.get_rule_map()


def clear_rule_cache(doc=None, method=None, *args, **kwargs):
	"""Selective runtime-registry invalidation for Rule lifecycle changes."""
	from flexirule.ruleflow.core.coordinator import RuleCoordinator

	if not doc:
		RuleCoordinator.clear_cache()
		return

	if RuleCoordinator.should_rebuild_registry_for_rule_change(doc, method):
		RuleCoordinator.clear_cache(doctype=doc.get("document_type"))
