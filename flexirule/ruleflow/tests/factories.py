import frappe

from flexirule.ruleflow.tests.test_doctypes import setup_test_doctypes


def make_test_contact(**kwargs):
	setup_test_doctypes()
	defaults = {
		"doctype": "Test Contact",
		"first_name": "John",
		"last_name": "Doe",
		"email_id": "john@example.com",
		"phone": "+1234567890",
		"status": "Open",
	}
	defaults.update(kwargs)
	doc = frappe.get_doc(defaults)
	if not kwargs.get("do_not_save"):
		doc.insert(ignore_permissions=True)
	return doc


def make_test_customer(**kwargs):
	setup_test_doctypes()
	defaults = {
		"doctype": "Test Customer",
		"customer_name": "Acme Corp",
		"email_id": "acme@example.com",
		"customer_group": "Commercial",
		"territory": "United States",
		"credit_limit": 5000,
		"status": "Active",
	}
	defaults.update(kwargs)
	doc = frappe.get_doc(defaults)
	if not kwargs.get("do_not_save"):
		doc.insert(ignore_permissions=True)
	return doc


def make_test_lead(**kwargs):
	setup_test_doctypes()
	defaults = {
		"doctype": "Test Lead",
		"first_name": "Jane",
		"email_id": "jane@example.com",
		"status": "Lead",
	}
	defaults.update(kwargs)
	doc = frappe.get_doc(defaults)
	if not kwargs.get("do_not_save"):
		doc.insert(ignore_permissions=True)
	return doc
