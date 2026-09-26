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
				"link_field": "customer",  # No doc. prefix
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

	@patch("frappe.db.get_value")
	def test_fetch_resolver_various_scopes(self, mock_get_value):
		mock_get_value.return_value = "Resolved"

		scopes = [
			("vars.link", "vars"),
			("loop.link", "loop"),
			("row.link", "row"),
			("item.link", "item"),
		]

		for path, scope in scopes:
			self.context[scope] = {"link": "LINK-001"}
			val = {
				"mode": "resolver",
				"config": {
					"kind": "fetch",
					"link_field": path,
					"fetch_field": "target",
					"linked_doctype": "TargetDT",
				},
			}
			resolver = ValueResolver.compile(val)
			result = resolver.resolve(self.context)
			self.assertEqual(result, "Resolved")
			mock_get_value.assert_called_with("TargetDT", "LINK-001", "target")

	def test_fetch_resolver_missing_link_field_scope(self):
		# link_field is None
		val = {
			"mode": "resolver",
			"config": {
				"kind": "fetch",
				"link_field": None,
				"fetch_field": "target",
				"linked_doctype": "TargetDT",
			},
		}
		resolver = ValueResolver.compile(val)
		self.assertIsNone(resolver.resolve(self.context))

	@patch("frappe.db.get_value")
	def test_canonical_lookup_static(self, mock_get_value):
		mock_get_value.return_value = "Commercial"
		val = {
			"family": "lookup",
			"operation": "fetch",
			"kind": "lookup",
			"config": {
				"doctype_mode": "static",
				"target_doctype": "Customer",
				"record_field": "customer",
				"fetch_field": "customer_group",
			},
		}
		resolver = ValueResolver.compile(val)
		result = resolver.resolve(self.context)
		mock_get_value.assert_called_once_with("Customer", "CUST-0001", "customer_group")
		self.assertEqual(result, "Commercial")

	@patch("frappe.db.get_value")
	def test_canonical_lookup_dynamic_customer(self, mock_get_value):
		mock_get_value.return_value = "Retail"
		self.doc.party_type = "Customer"
		self.doc.party = "CUST-0001"

		val = {
			"family": "lookup",
			"operation": "fetch",
			"kind": "lookup",
			"config": {
				"doctype_mode": "dynamic",
				"doctype_source": "party_type",
				"record_field": "party",
				"fetch_field": "customer_group",
			},
		}
		resolver = ValueResolver.compile(val)
		result = resolver.resolve(self.context)
		mock_get_value.assert_called_once_with("Customer", "CUST-0001", "customer_group")
		self.assertEqual(result, "Retail")

	@patch("frappe.db.get_value")
	def test_canonical_lookup_dynamic_supplier(self, mock_get_value):
		mock_get_value.return_value = "Services"
		self.doc.party_type = "Supplier"
		self.doc.party = "SUP-0001"

		val = {
			"family": "lookup",
			"operation": "fetch",
			"kind": "lookup",
			"config": {
				"doctype_mode": "dynamic",
				"doctype_source": "party_type",
				"record_field": "party",
				"fetch_field": "supplier_group",
			},
		}
		resolver = ValueResolver.compile(val)
		result = resolver.resolve(self.context)
		mock_get_value.assert_called_once_with("Supplier", "SUP-0001", "supplier_group")
		self.assertEqual(result, "Services")

	@patch("frappe.db.get_value")
	def test_canonical_lookup_child_table_row_context(self, mock_get_value):
		mock_get_value.return_value = "Hardware"
		self.context["row"] = {"party_type": "Supplier", "party": "SUP-0099"}

		val = {
			"family": "lookup",
			"operation": "fetch",
			"kind": "lookup",
			"config": {
				"doctype_mode": "dynamic",
				"doctype_source": "party_type",
				"record_field": "party",
				"fetch_field": "supplier_type",
			},
		}
		resolver = ValueResolver.compile(val)
		result = resolver.resolve(self.context)
		mock_get_value.assert_called_once_with("Supplier", "SUP-0099", "supplier_type")
		self.assertEqual(result, "Hardware")

	@patch("frappe.db.get_value")
	def test_canonical_lookup_missing_doctype_source(self, mock_get_value):
		self.doc.party_type = None
		self.doc.party = "CUST-0001"

		val = {
			"family": "lookup",
			"operation": "fetch",
			"kind": "lookup",
			"config": {
				"doctype_mode": "dynamic",
				"doctype_source": "party_type",
				"record_field": "party",
				"fetch_field": "customer_group",
			},
		}
		resolver = ValueResolver.compile(val)
		result = resolver.resolve(self.context)
		self.assertIsNone(result)
		mock_get_value.assert_not_called()

	@patch("frappe.db.get_value")
	def test_canonical_lookup_missing_record_field(self, mock_get_value):
		self.doc.party_type = "Customer"
		self.doc.party = None

		val = {
			"family": "lookup",
			"operation": "fetch",
			"kind": "lookup",
			"config": {
				"doctype_mode": "dynamic",
				"doctype_source": "party_type",
				"record_field": "party",
				"fetch_field": "customer_group",
			},
		}
		resolver = ValueResolver.compile(val)
		result = resolver.resolve(self.context)
		self.assertIsNone(result)
		mock_get_value.assert_not_called()

	def test_canonical_lookup_invalid_doctype(self):
		self.doc.party_type = "NonExistentDocType_XYZ"
		self.doc.party = "123"

		val = {
			"family": "lookup",
			"operation": "fetch",
			"kind": "lookup",
			"config": {
				"doctype_mode": "dynamic",
				"doctype_source": "party_type",
				"record_field": "party",
				"fetch_field": "customer_group",
			},
		}
		resolver = ValueResolver.compile(val)
		result = resolver.resolve(self.context)
		self.assertIsNone(result)

	@patch("frappe.has_permission", return_value=False)
	def test_canonical_lookup_permission_denied(self, mock_has_perm):
		self.doc.party_type = "Customer"
		self.doc.party = "CUST-0001"

		val = {
			"family": "lookup",
			"operation": "fetch",
			"kind": "lookup",
			"config": {
				"doctype_mode": "dynamic",
				"doctype_source": "party_type",
				"record_field": "party",
				"fetch_field": "customer_group",
			},
		}
		resolver = ValueResolver.compile(val)
		current_user = frappe.session.user if getattr(frappe, "session", None) else "Administrator"
		try:
			frappe.set_user("restricted_user")
			with self.assertRaises(frappe.PermissionError):
				resolver.resolve(self.context)
		finally:
			frappe.set_user(current_user)
