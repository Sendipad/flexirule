import frappe


def execute():
	"""
	Set default action_config_mode to 'Dialog' for RuleFlow Settings.
	"""
	frappe.db.set_single_value("RuleFlow Settings", "action_config_mode", "Dialog")
