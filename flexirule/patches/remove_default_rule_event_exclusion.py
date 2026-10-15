import frappe


def execute():
	"""Remove Rule from the legacy default exclusion list once.

	Rule lifecycle events are now supported. This removes the old seeded default
	from existing sites, but the settings UI remains authoritative: an
	administrator can explicitly re-add Rule to the exclusion list later.
	"""
	if not frappe.db.exists("DocType", "RuleFlow Settings"):
		return

	settings = frappe.get_doc("RuleFlow Settings")
	exclusions = settings.get("excluded_doctypes") or []
	retained = [row for row in exclusions if row.document_type != "Rule"]

	if len(retained) != len(exclusions):
		settings.set("excluded_doctypes", retained)
		settings.save(ignore_permissions=True)
