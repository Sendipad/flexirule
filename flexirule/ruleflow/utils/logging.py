# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

"""
Logging utilities for FlexiRule rule execution.
Provides transaction-safe logging that survives rollbacks.

IMPORTANT — Transaction Boundary Design Note
=============================================
``persist_execution_log`` is **always** invoked inside a background job
(via ``frappe.enqueue``) from ``RuleEngine._save_execution_log``. This
means it runs in its **own RQ worker process** with a **separate database
connection** — it does NOT share the caller's transaction.

The explicit ``frappe.db.commit()`` is therefore required to flush the
INSERT to disk before the worker connection closes.  Without it, the log
row would be rolled back when the RQ worker's implicit rollback fires on
connection teardown.

The ``frappe.flags.in_test`` guard skips the commit during unit tests
because tests run inside a single transaction that is rolled back after
each test method (Frappe's ``IntegrationTestCase`` pattern).
"""

import frappe


def persist_execution_log(log_data: dict, *, skip_commit: bool = False):
	"""Persist an execution log entry.

	Called via ``frappe.enqueue`` so the log survives even when the main
	request transaction rolls back (e.g. on ``ValidationError``).

	Args:
		log_data: Dictionary containing all fields for Rule Execution Log.
		skip_commit: When *True*, skip the explicit commit.  Useful for
			callers that manage their own transaction (e.g. batch
			importers or custom test harnesses).
	"""
	try:
		log_doc = frappe.get_doc({"doctype": "Rule Execution Log", **log_data})
		log_doc.insert(ignore_permissions=True, ignore_links=True)

		# Commit only when running inside a background worker AND not in
		# the test harness.  See module-level docstring for rationale.
		if not skip_commit and not getattr(frappe.flags, "in_test", False):
			frappe.db.commit()
	except Exception as exc:
		frappe.logger("flexirule.logging").error(
			f"Failed to persist Rule Execution Log: {exc!s}",
			exc_info=True,
		)
