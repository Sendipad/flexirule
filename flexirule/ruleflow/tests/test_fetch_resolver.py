import unittest
from unittest.mock import patch
import frappe
from flexirule.ruleflow.core.value_resolver import ValueResolver

class TestFetchResolver(unittest.TestCase):
	def setUp(self):
		self.doc = frappe._dict(
			{
				"doctype": "User",
				"customer": "CUST-0001",
			}
		)
		self.context = {"doc": self.doc, "vars": {}}

	@patch("frappe.db.get_value")
	def test_fetch_resolver_with_prefix(self, mock_get_value):
		mock_get_value.return_value = "PM-0005"

		val = {
			"mode": "resolver",
			"config": {
				"kind": "fetch",
				"link_field": "doc.customer",
				"fetch_field": "party_master",
				"linked_doctype": "Customer",
			},
		}
		resolver = ValueResolver.compile(val)
		result = resolver.resolve(self.context)

		mock_get_value.assert_called_once_with("Customer", "CUST-0001", "party_master")
		self.assertEqual(result, "PM-0005")

	@patch("frappe.db.get_value")
	def test_fetch_resolver_without_prefix(self, mock_get_value):
		mock_get_value.return_value = "PM-0005"

		val = {
			"mode": "resolver",
			"config": {
				"kind": "fetch",
				"link_field": "customer", # No doc. prefix
				"fetch_field": "party_master",
				"linked_doctype": "Customer",
			},
		}
		resolver = ValueResolver.compile(val)
		result = resolver.resolve(self.context)

		# Should still resolve correctly by prepending doc.
		mock_get_value.assert_called_once_with("Customer", "CUST-0001", "party_master")
		self.assertEqual(result, "PM-0005")

	def test_fetch_resolver_missing_config(self):
		val = {
			"mode": "resolver",
			"config": {
				"kind": "fetch",
				"link_field": "doc.customer",
				# fetch_field missing
				"linked_doctype": "Customer",
			},
		}
		resolver = ValueResolver.compile(val)
		result = resolver.resolve(self.context)
		self.assertIsNone(result)

	@patch("frappe.db.get_value")
	def test_fetch_resolver_no_link_value(self, mock_get_value):
		self.doc.customer = None
		val = {
			"mode": "resolver",
			"config": {
				"kind": "fetch",
				"link_field": "doc.customer",
				"fetch_field": "party_master",
				"linked_doctype": "Customer",
			},
		}
		resolver = ValueResolver.compile(val)
		result = resolver.resolve(self.context)
		self.assertIsNone(result)
		mock_get_value.assert_not_called()
