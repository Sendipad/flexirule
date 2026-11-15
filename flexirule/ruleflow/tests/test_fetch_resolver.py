import unittest
from types import SimpleNamespace
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
		self.meta_fields = {
			"Customer": {"name", "customer_group"},
			"Supplier": {"name", "supplier_group", "supplier_type"},
			"User": {"name", "email"},
			"TargetDT": {"name", "email"},
			"Secret Record": {"name", "secret"},
		}
		self.meta_patch = patch("frappe.get_meta", side_effect=self._get_meta)
		self.permitted_fields_patch = patch(
			"frappe.model.get_permitted_fields", side_effect=self._get_permitted_fields
		)
		self.select_permission_patch = patch("frappe.only_has_select_perm", return_value=False)
		for patcher in (self.meta_patch, self.permitted_fields_patch, self.select_permission_patch):
			patcher.start()
			self.addCleanup(patcher.stop)

	def _get_meta(self, doctype):
		if doctype not in self.meta_fields:
			raise frappe.DoesNotExistError
		return SimpleNamespace(
			issingle=False,
			istable=False,
			get_valid_columns=lambda: list(self.meta_fields[doctype]),
			get_field=lambda fieldname: SimpleNamespace(
				fieldtype="Password" if fieldname == "secret" else "Data"
			)
			if fieldname in self.meta_fields[doctype]
			else None,
		)

	def _get_permitted_fields(self, doctype, permission_type=None):
		return list(self.meta_fields.get(doctype, {"name"}))

	@patch("frappe.get_list")
	def test_fetch_resolver_with_prefix(self, mock_get_value):
		mock_get_value.return_value = [{"customer_group": "PM-0005"}]

		val = {
			"mode": "resolver",
			"config": {
				"kind": "fetch",
				"link_field": "doc.customer",
				"fetch_field": "customer_group",
				"linked_doctype": "Customer",
			},
		}
		resolver = ValueResolver.compile(val)
		result = resolver.resolve(self.context)

		mock_get_value.assert_called_once_with(
			"Customer", filters={"name": "CUST-0001"}, fields=["customer_group"], limit_page_length=1
		)
		self.assertEqual(result, "PM-0005")

	@patch("frappe.get_list")
	def test_fetch_resolver_without_prefix(self, mock_get_value):
		mock_get_value.return_value = [{"customer_group": "PM-0005"}]

		val = {
			"mode": "resolver",
			"config": {
				"kind": "fetch",
				"link_field": "customer",  # No doc. prefix
				"fetch_field": "customer_group",
				"linked_doctype": "Customer",
			},
		}
		resolver = ValueResolver.compile(val)
		result = resolver.resolve(self.context)

		# Should still resolve correctly by prepending doc.
		mock_get_value.assert_called_once_with("Customer", filters={"name": "CUST-0001"}, fields=["customer_group"], limit_page_length=1)
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

	@patch("frappe.get_list")
	def test_fetch_resolver_no_link_value(self, mock_get_value):
		self.doc.customer = None
		val = {
			"mode": "resolver",
			"config": {
				"kind": "fetch",
				"link_field": "doc.customer",
				"fetch_field": "customer_group",
				"linked_doctype": "Customer",
			},
		}
		resolver = ValueResolver.compile(val)
		result = resolver.resolve(self.context)
		self.assertIsNone(result)
		mock_get_value.assert_not_called()

	@patch("frappe.get_list")
	def test_fetch_resolver_various_scopes(self, mock_get_value):
		mock_get_value.return_value = [{"email": "Resolved"}]

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
					"fetch_field": "email",
					"linked_doctype": "User",
				},
			}
			resolver = ValueResolver.compile(val)
			result = resolver.resolve(self.context)
			self.assertEqual(result, "Resolved")
			mock_get_value.assert_called_with(
				"User", filters={"name": "LINK-001"}, fields=["email"], limit_page_length=1
			)

	def test_fetch_resolver_missing_link_field_scope(self):
		# link_field is None
		val = {
			"mode": "resolver",
			"config": {
				"kind": "fetch",
				"link_field": None,
				"fetch_field": "email",
				"linked_doctype": "User",
			},
		}
		resolver = ValueResolver.compile(val)
		self.assertIsNone(resolver.resolve(self.context))

	@patch("frappe.get_list")
	def test_canonical_lookup_static(self, mock_get_value):
		mock_get_value.return_value = [{"customer_group": "Commercial"}]
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
		mock_get_value.assert_called_once_with("Customer", filters={"name": "CUST-0001"}, fields=["customer_group"], limit_page_length=1)
		self.assertEqual(result, "Commercial")

	@patch("frappe.get_list")
	def test_canonical_lookup_dynamic_customer(self, mock_get_value):
		mock_get_value.return_value = [{"customer_group": "Retail"}]
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
		mock_get_value.assert_called_once_with("Customer", filters={"name": "CUST-0001"}, fields=["customer_group"], limit_page_length=1)
		self.assertEqual(result, "Retail")

	@patch("frappe.get_list")
	def test_canonical_lookup_dynamic_supplier(self, mock_get_value):
		mock_get_value.return_value = [{"supplier_group": "Services"}]
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
		mock_get_value.assert_called_once_with(
			"Supplier", filters={"name": "SUP-0001"}, fields=["supplier_group"], limit_page_length=1
		)
		self.assertEqual(result, "Services")

	@patch("frappe.get_list")
	def test_canonical_lookup_child_table_row_context(self, mock_get_value):
		mock_get_value.return_value = [{"supplier_type": "Hardware"}]
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
		mock_get_value.assert_called_once_with(
			"Supplier", filters={"name": "SUP-0099"}, fields=["supplier_type"], limit_page_length=1
		)
		self.assertEqual(result, "Hardware")

	@patch("frappe.get_list")
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

	@patch("frappe.get_list")
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

	@patch("frappe.model.get_permitted_fields", return_value=["name"])
	@patch("frappe.get_list")
	def test_canonical_lookup_denies_field_without_fieldlevel_read_permission(
		self, mock_get_list, mock_get_permitted_fields
	):
		self.doc.party_type = "Customer"
		self.doc.party = "CUST-0001"
		resolver = ValueResolver.compile(
			{
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
		)
		with self.assertRaises(frappe.PermissionError):
			resolver.resolve(self.context)
		mock_get_list.assert_not_called()
		mock_get_permitted_fields.assert_called_once()

	@patch("frappe.get_list")
	def test_canonical_lookup_rejects_password_fields(self, mock_get_list):
		resolver = ValueResolver.compile(
			{
				"family": "lookup",
				"operation": "fetch",
				"kind": "lookup",
				"config": {
					"doctype_mode": "static",
					"target_doctype": "Secret Record",
					"record_field": "customer",
					"fetch_field": "secret",
				},
			}
		)
		with self.assertRaises(frappe.PermissionError):
			resolver.resolve(self.context)
		mock_get_list.assert_not_called()

	@patch("frappe.get_list", return_value=[])
	def test_canonical_lookup_respects_record_permission_filters(self, mock_get_list):
		self.doc.party_type = "Customer"
		self.doc.party = "CUST-0001"
		resolver = ValueResolver.compile(
			{
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
		)
		self.assertIsNone(resolver.resolve(self.context))
		mock_get_list.assert_called_once_with(
			"Customer",
			filters={"name": "CUST-0001"},
			fields=["customer_group"],
			limit_page_length=1,
		)

	@patch("frappe.get_list", side_effect=frappe.PermissionError)
	def test_canonical_lookup_permission_denied(self, mock_get_list):
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
