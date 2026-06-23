import frappe


def after_install():
	"""
	Run setup tasks after the FlexiRule app is installed.
	"""
	setup_default_ruleflow_settings()
	setup_action_types()


def setup_action_types():
	"""
	Seed the Action Type registry with default types.
	"""
	from flexirule.ruleflow.utils.action_type_registry import seed_default_action_types

	seed_default_action_types()


def setup_default_ruleflow_settings():
	"""
	Populate the RuleFlow Settings singleton with default values,
	including a default list of excluded DocTypes.
	"""
	settings = frappe.get_doc("RuleFlow Settings")

	default_doctypes = [
		"Rule",
		"Rule Execution Log",
		"Rule Scheduler",
		"Error Log",
		"Activity Log",
		"Access Log",
		"Email Queue",
		"Scheduled Job Log",
		"Version",
		"Comment",
		"Communication",
		"File",
	]

	existing_doctypes = [row.document_type for row in settings.excluded_doctypes]

	for dt in default_doctypes:
		if dt not in existing_doctypes and frappe.db.exists("DocType", dt):
			settings.append("excluded_doctypes", {"document_type": dt})

	settings.save(ignore_permissions=True)
