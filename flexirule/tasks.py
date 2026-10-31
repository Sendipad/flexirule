import frappe
from frappe.utils import add_days


def clear_old_logs():
	"""
	Scheduled Job: Daily
	Clears Rule Execution Logs older than 30 days.
	Configurable via global system settings (RuleFlow Settings), default to 30.
	"""
	retention_days = frappe.db.get_single_value("RuleFlow Settings", "log_retention_days") or 30
	cutoff_date = add_days(frappe.utils.nowdate(), -retention_days)

	frappe.db.sql(
		"""
		DELETE FROM `tabRule Execution Log`
		WHERE creation < %s
	""",
		(cutoff_date,),
	)

	frappe.db.commit()  # nosemgrep: frappe-manual-commit
