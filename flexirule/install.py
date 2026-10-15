import frappe


def after_install():
	"""
	Run setup tasks after the FlexiRule app is installed.
	"""
	setup_default_ruleflow_settings()
	setup_action_types()
	register_system_rules()


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

	# Rule is now eligible for self-hosting RuleFlow events. Remove the
	# legacy default exclusion from existing sites as well as fresh installs.
	settings.excluded_doctypes = [row for row in settings.excluded_doctypes if row.document_type != "Rule"]
	existing_doctypes = [row.document_type for row in settings.excluded_doctypes]

	for dt in default_doctypes:
		if dt not in existing_doctypes and frappe.db.exists("DocType", dt):
			settings.append("excluded_doctypes", {"document_type": dt})

	settings.save(ignore_permissions=True)


_DEPRECATED_SYSTEM_RULE_BASE_NAMES = (
	"RULE_NAMING_REJECT_EMPTY_OR_PLACEHOLDER",
)


def retire_deprecated_system_rules():
	"""Disable retired app-managed policies while preserving their audit history."""
	for logical_name in _DEPRECATED_SYSTEM_RULE_BASE_NAMES:
		rule_names = set(
			frappe.get_all(
				"Rule",
				filters={"base_rule_name": logical_name, "is_system_generated": 1},
				pluck="name",
			)
		)
		exact_name = frappe.db.get_value("Rule", {"rule_name": logical_name}, "name")
		if exact_name and frappe.db.get_value("Rule", exact_name, "is_system_generated"):
			rule_names.add(exact_name)

		for name in rule_names:
			rule = frappe.get_doc("Rule", name)
			if not rule.is_system_generated:
				continue
			if rule.is_active or rule.status != "Disabled":
				rule.is_active = 0
				rule.status = "Disabled"
				rule.save(ignore_permissions=True)


def register_system_rules():
	"""Register current definitions, then retire explicitly deprecated policies."""
	from flexirule.ruleflow.core.system_rule_registry import register_configured_system_rules

	register_configured_system_rules()
	retire_deprecated_system_rules()
