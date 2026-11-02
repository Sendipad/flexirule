# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

from collections.abc import Iterable, Sequence

import frappe


def safe_cleanup_test_resources(
	doctypes: Iterable[str] | None = None,
	records: Sequence[tuple[str, str]] | None = None,
) -> None:
	"""
	Idempotently cleans up dynamically created test records and DocTypes.
	Executes via try/finally semantics, deleting records first, then DocTypes,
	and safely removing orphaned physical tables if native DocType deletion left them behind.
	Never silently swallows errors; raises the first encountered exception after completing
	all cleanup steps.
	"""
	errors: list[Exception] = []

	# Step 1: Clean up records in reverse order
	if records:
		for item in reversed(records):
			try:
				dt, dn = item
				if frappe.db.exists(dt, dn):
					frappe.delete_doc(dt, dn, force=True, ignore_permissions=True)
			except Exception as e:
				errors.append(e)

	# Step 2: Clean up DocTypes in reverse order
	if doctypes:
		for dt in reversed(list(doctypes)):
			try:
				if frappe.db.exists("DocType", dt):
					frappe.delete_doc("DocType", dt, force=True, ignore_permissions=True)
			except Exception as e:
				errors.append(e)

			# Verify if physical table was left behind and clean up if needed
			try:
				if frappe.db.table_exists(dt):
					frappe.db.sql_ddl(f"DROP TABLE IF EXISTS `tab{dt}`")
			except Exception as e:
				errors.append(e)

	try:
		frappe.db.commit()
		frappe.clear_cache()
	except Exception as e:
		errors.append(e)

	if errors:
		raise errors[0]
