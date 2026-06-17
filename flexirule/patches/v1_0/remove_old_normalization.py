import frappe


def execute():
	"""
	Remove the old 'Normalization' Process and clean up Rule Actions referencing it.
	"""
	# 1. Delete the 'Normalization' Process document
	if frappe.db.exists("Process", "Normalization"):
		frappe.delete_doc("Process", "Normalization", ignore_permissions=True, force=True)

	# 2. Find and clean up Rule Actions referencing the old process
	# We can either delete them or mark them as disabled to avoid breaking the rule flow silently.
	# Given the instructions for a "clean, cascading delete", we'll remove them.
	rule_actions = frappe.get_all("Rule Action", filters={"process_name": "Normalization"}, pluck="name")

	for action_name in rule_actions:
		frappe.delete_doc("Rule Action", action_name, ignore_permissions=True, force=True)

	# Clear cache to ensure changes are reflected
	frappe.clear_cache()
