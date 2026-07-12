import frappe


def execute():
	"""Migrate data from deprecated skip_permissions to ignore_permissions."""
	if not frappe.db.has_column("Rule Action", "skip_permissions"):
		return

	if not frappe.db.has_column("Rule Action", "ignore_permissions"):
		frappe.reload_doc("ruleflow", "doctype", "rule_action")

	frappe.db.sql("""
		UPDATE `tabRule Action`
		SET ignore_permissions = skip_permissions
		WHERE skip_permissions = 1
	""")
