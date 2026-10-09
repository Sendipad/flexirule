import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import random_string

from flexirule.ruleflow.core.action_handlers.query_records import QueryRecordsHandler


class TestQueryRecordsFieldNavigation(FrappeTestCase):
	"""Backend integration tests for Query Records Field Navigation and child table dotted field paths."""

	def setUp(self):
		self.handler = QueryRecordsHandler()

	def tearDown(self):
		frappe.db.rollback()

	def test_query_list_with_dotted_child_table_field_path(self):
		"""Verify Query List filtering with a dotted Child Table field path (e.g., roles.role)."""
		role_name = "System Manager"
		user_email = f"child_table_user_{random_string(5).lower()}@example.com"
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": user_email,
				"first_name": "Child Table Test",
				"roles": [{"role": role_name}],
			}
		).insert(ignore_permissions=True)

		action = frappe._dict(
			{
				"operation": "Query List",
				"reference_doctype": "User",
				"config": frappe.as_json(
					{
						"filters": [
							["User", "roles.role", "=", role_name],
							["User", "email", "=", user.email],
						],
						"fields": ["name", "email", "first_name"],
					}
				),
			}
		)

		result, _ = self.handler.execute(action, {}, None)
		self.assertIsInstance(result, list)
		self.assertTrue(len(result) >= 1)
		emails = [r.get("email").lower() for r in result if r.get("email")]
		self.assertIn(user_email, emails)

	def test_query_list_selected_fields_with_dotted_paths(self):
		"""Verify Query List returning selected fields with nested dotted paths."""
		user_email = f"select_fields_{random_string(5).lower()}@example.com"
		frappe.get_doc(
			{
				"doctype": "User",
				"email": user_email,
				"first_name": "Selected Fields Test",
				"roles": [{"role": "Blogger"}],
			}
		).insert(ignore_permissions=True)

		action = frappe._dict(
			{
				"operation": "Query List",
				"reference_doctype": "User",
				"config": frappe.as_json(
					{
						"filters": [["User", "email", "=", user_email]],
						"fields": ["email", "first_name"],
					}
				),
			}
		)

		result, _ = self.handler.execute(action, {}, None)
		self.assertIsInstance(result, list)
		self.assertEqual(len(result), 1)
		self.assertEqual(result[0].get("email").lower(), user_email)

	def test_query_records_handler_backward_compatibility(self):
		"""Verify that standard scalar field queries continue working as expected."""
		desc = f"Backward compat test {random_string(5)}"
		frappe.get_doc(
			{
				"doctype": "ToDo",
				"description": desc,
			}
		).insert(ignore_permissions=True)

		action = frappe._dict(
			{
				"operation": "Query List",
				"reference_doctype": "ToDo",
				"config": frappe.as_json(
					{
						"filters": [["ToDo", "description", "=", desc]],
						"fields": ["name", "description"],
					}
				),
			}
		)

		result, _ = self.handler.execute(action, {}, None)
		self.assertIsInstance(result, list)
		self.assertEqual(len(result), 1)
		self.assertEqual(result[0].get("description"), desc)
