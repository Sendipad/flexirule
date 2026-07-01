import frappe
from frappe.model.docstatus import DocStatus


def setup_test_doctypes():
	"""Create minimal DocTypes for testing if they don't exist."""
	create_test_contact_doctype()
	create_test_customer_doctype()
	create_test_lead_doctype()


def create_test_contact_doctype():
	if frappe.db.exists("DocType", "Test Contact"):
		return

	frappe.get_doc(
		{
			"doctype": "DocType",
			"name": "Test Contact",
			"module": "RuleFlow",
			"custom": 1,
			"autoname": "hash",
			"fields": [
				{"fieldname": "first_name", "label": "First Name", "fieldtype": "Data", "reqd": 1},
				{"fieldname": "last_name", "label": "Last Name", "fieldtype": "Data"},
				{"fieldname": "email_id", "label": "Email", "fieldtype": "Data"},
				{"fieldname": "phone", "label": "Phone", "fieldtype": "Data"},
				{
					"fieldname": "status",
					"label": "Status",
					"fieldtype": "Select",
					"options": "Open\nClosed\nPassive",
				},
				{"fieldname": "mobile_no", "label": "Mobile No", "fieldtype": "Data"},
			],
			"permissions": [{"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1}],
		}
	).insert(ignore_permissions=True)


def create_test_customer_doctype():
	if frappe.db.exists("DocType", "Test Customer"):
		return

	frappe.get_doc(
		{
			"doctype": "DocType",
			"name": "Test Customer",
			"module": "RuleFlow",
			"custom": 1,
			"autoname": "hash",
			"fields": [
				{"fieldname": "customer_name", "label": "Customer Name", "fieldtype": "Data", "reqd": 1},
				{"fieldname": "email_id", "label": "Email", "fieldtype": "Data"},
				{"fieldname": "customer_group", "label": "Customer Group", "fieldtype": "Data"},
				{"fieldname": "territory", "label": "Territory", "fieldtype": "Data"},
				{"fieldname": "credit_limit", "label": "Credit Limit", "fieldtype": "Currency"},
				{
					"fieldname": "status",
					"label": "Status",
					"fieldtype": "Select",
					"options": "Active\nInactive\nSuspended",
				},
			],
			"permissions": [{"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1}],
		}
	).insert(ignore_permissions=True)


def create_test_lead_doctype():
	if frappe.db.exists("DocType", "Test Lead"):
		return

	frappe.get_doc(
		{
			"doctype": "DocType",
			"name": "Test Lead",
			"module": "RuleFlow",
			"custom": 1,
			"autoname": "hash",
			"fields": [
				{"fieldname": "first_name", "label": "First Name", "fieldtype": "Data", "reqd": 1},
				{"fieldname": "email_id", "label": "Email", "fieldtype": "Data"},
				{"fieldname": "phone", "label": "Phone", "fieldtype": "Data"},
				{
					"fieldname": "status",
					"label": "Status",
					"fieldtype": "Select",
					"options": "Lead\nInterested\nConverted",
				},
			],
			"permissions": [{"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1}],
		}
	).insert(ignore_permissions=True)
