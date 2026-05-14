# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.process.deduplication.deduplication import (
	find_duplicates_in_child_table,
)


class TestContactDeduplication(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")

	def setUp(self):
		# Create a base contact
		self.phone_number = "9998887776"
		self.contact1 = frappe.get_doc(
			{
				"doctype": "Contact",
				"first_name": "Original",
				"last_name": "Contact",
				"phone_nos": [{"phone": self.phone_number, "is_primary_phone": 1}],
			}
		).insert(ignore_permissions=True)

	def tearDown(self):
		frappe.db.rollback()

	def test_dedup_by_phone_child_table(self):
		"""Test finding duplicate contact via child table phone number"""

		# Create a new (unsaved) contact with SAME phone number
		contact2 = frappe.get_doc(
			{
				"doctype": "Contact",
				"first_name": "Duplicate",
				"last_name": "Entry",
				"phone_nos": [
					{"phone": self.phone_number}  # Same phone
				],
			}
		)

		context = {"doc": contact2, "vars": {}}

		# Run dedup check
		duplicates = find_duplicates_in_child_table(
			context, {"child_table_field": "phone_nos", "child_search_field": "phone"}
		)

		match_names = [m["name"] for m in duplicates.get("matches", [])]
		self.assertIn(self.contact1.name, match_names)

	def test_dedup_multiple_numbers(self):
		"""Test matching when one of multiple numbers matches"""
		contact3 = frappe.get_doc(
			{
				"doctype": "Contact",
				"first_name": "Multi",
				"phone_nos": [
					{"phone": "1112223333"},
					{"phone": self.phone_number},  # This one matches
				],
			}
		)

		context = {"doc": contact3, "vars": {}}
		duplicates = find_duplicates_in_child_table(
			context, {"child_table_field": "phone_nos", "child_search_field": "phone"}
		)

		match_names = [m["name"] for m in duplicates.get("matches", [])]
		self.assertIn(self.contact1.name, match_names)

	def test_no_false_positive(self):
		"""Test unique number returns no duplicates"""
		contact_unique = frappe.get_doc(
			{
				"doctype": "Contact",
				"first_name": "Unique",
				"phone_nos": [
					{"phone": "0000000000"}  # Unique
				],
			}
		)

		context = {"doc": contact_unique, "vars": {}}
		duplicates = find_duplicates_in_child_table(
			context, {"child_table_field": "phone_nos", "child_search_field": "phone"}
		)

		self.assertEqual(duplicates.get("match_count"), 0)
