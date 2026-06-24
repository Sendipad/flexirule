# Copyright (c) 2026, Abdo Ruzaqi and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestActionType(FrappeTestCase):
	def setUp(self):
		# Ensure clean state for tests
		if frappe.db.exists("Action Type", "Test Action"):
			frappe.db.delete("Action Type", "Test Action")

	def test_creation_restriction(self):
		"""Test that creating Action Type is restricted without flags"""
		doc = frappe.new_doc("Action Type")
		doc.name = "Test Action"
		doc.category = "Flow Control"

		# Should fail without flags
		self.assertRaises(frappe.ValidationError, doc.insert)

	def test_creation_with_migrate_flag(self):
		"""Test that creating Action Type is allowed with in_migrate flag"""
		frappe.flags.in_migrate = True
		try:
			doc = frappe.get_doc(
				{"doctype": "Action Type", "name": "Test Action", "category": "Flow Control"}
			)
			doc.insert()
			self.assertTrue(frappe.db.exists("Action Type", "Test Action"))
		finally:
			frappe.flags.in_migrate = False

	def test_update_restriction(self):
		"""Test that updating Action Type is restricted without flags"""
		# First create one with flag
		frappe.flags.in_migrate = True
		doc = frappe.get_doc(
			{"doctype": "Action Type", "name": "Test Action", "category": "Flow Control"}
		).insert()
		frappe.flags.in_migrate = False

		# Now try to update it
		doc.description = "Updated description"
		self.assertRaises(frappe.ValidationError, doc.save)

	def test_rename_restriction(self):
		"""Test that renaming Action Type is restricted without flags"""
		frappe.flags.in_migrate = True
		frappe.get_doc({"doctype": "Action Type", "name": "Test Action", "category": "Flow Control"}).insert()
		frappe.flags.in_migrate = False

		self.assertRaises(
			frappe.ValidationError, frappe.rename_doc, "Action Type", "Test Action", "Renamed Action"
		)

	def test_delete_restriction(self):
		"""Test that deleting Action Type is restricted without flags"""
		frappe.flags.in_migrate = True
		frappe.get_doc({"doctype": "Action Type", "name": "Test Action", "category": "Flow Control"}).insert()
		frappe.flags.in_migrate = False

		self.assertRaises(frappe.ValidationError, frappe.delete_doc, "Action Type", "Test Action")

	def tearDown(self):
		frappe.flags.in_migrate = True
		if frappe.db.exists("Action Type", "Test Action"):
			frappe.delete_doc("Action Type", "Test Action")
		frappe.flags.in_migrate = False
